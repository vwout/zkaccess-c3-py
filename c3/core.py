from __future__ import annotations

import logging
import re
import socket
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional

from c3 import consts, controldevice, crc, rtlog, utils


@dataclass
class C3DeviceInfo:
    """Basic C3 panel (connection) information, obtained from discovery"""
    host: str
    port: int = consts.C3_PORT_DEFAULT
    serial_number: str = None
    mac: str = None
    device_name: str = None
    firmware_version: str = None


@dataclass
class C3DoorSettings:
    """C3 panel door configuration and settings"""
    sensor_type: consts.DoorSensorType = consts.DoorSensorType.NONE
    """Door sensor type
    
    parameter: DoorNSensorType,
    0: Not available
    1: Normal open
    2: Normal closed 
    """
    lock_drive_time: int = None
    """Lock driver time length
    
    parameter: DoorNDrivertime,
    The value range is 0 to 255.
    0: Normal closed
    255: Normal open
    1 to 254: Door-opening duration
    """
    door_alarm_timeout: int = None
    """Timeout alarm duration of door magnet
    
    parameter: DoorNDetectortime
    The value range is 0 to 255,
    Unit: second
    """


@dataclass
class C3PanelStatus:
    """C3 panel peripheral status"""
    nr_of_locks: int = 0
    nr_aux_in: int = 0
    nr_aux_out: int = 0
    door_settings: Dict[int, C3DoorSettings] = field(default_factory=dict)
    lock_status: Dict[int, consts.InOutStatus] = field(default_factory=dict)
    aux_in_status: Dict[int, consts.InOutStatus] = field(default_factory=dict)
    aux_out_status: Dict[int, consts.InOutStatus] = field(default_factory=dict)


class C3:
    log = logging.getLogger("C3")
    log.setLevel(logging.ERROR)
    receive_timeout = 1
    receive_retries = 3

    def __init__(self, host: [str | C3DeviceInfo], port: int = consts.C3_PORT_DEFAULT) -> None:
        self._sock: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.receive_timeout)
        self._connected: bool = False
        self._session_less = False
        self._initialized = False
        self._protocol_version = None
        self._rtlog_command = consts.Command.RTLOG_BINARY
        self._session_id: int = 0xFEFE
        self._request_nr: int = -258
        self._status: C3PanelStatus = C3PanelStatus()
        if isinstance(host, C3DeviceInfo):
            self._device_info: C3DeviceInfo = host
        elif isinstance(host, str):
            self._device_info: C3DeviceInfo = C3DeviceInfo(host=host, port=port or consts.C3_PORT_DEFAULT)

    @classmethod
    def _get_message_header(cls, data: [bytes or bytearray]) -> tuple[[int or None], int, int]:
        if len(data) >= 5:
            version = data[1]
            if data[0] == consts.C3_MESSAGE_START:  # and version == consts.C3_PROTOCOL_VERSION:
                command = data[2]
                data_size = data[3] + (data[4] * 256)
            else:
                raise ValueError("Received reply does not start with start token")
        else:
            raise ValueError(f"Received reply of insufficient length {len(data)}")

        return command, data_size, version

    @classmethod
    def _get_message(cls, data: [bytes or bytearray]) -> bytearray:
        if data[-1] == consts.C3_MESSAGE_END:
            # Get the message payload, without start, crc and end bytes
            checksum = crc.crc16(data[1:-3])

            if utils.lsb(checksum) == data[-3] or utils.msb(checksum) == data[-2]:
                # Return all data without header (leading) and crc (trailing)
                message = bytearray(data[5:-3])
            else:
                raise ValueError("Payload checksum is invalid: %02x%02x expected %02x%02x" %
                                 (data[-3], data[-2], utils.lsb(checksum), utils.msb(checksum)))
        else:
            raise ValueError("Payload does not include message end marker (%02x)" % data[-1])

        return message

    @classmethod
    def _construct_message(cls, session_id: Optional[int], request_nr: Optional[int], command: consts.Command,
                           data=None) -> bytes:
        message_length = len(data or []) + (4 if (session_id and request_nr) else 0)
        message = bytearray([consts.C3_PROTOCOL_VERSION,
                             command or 0x00,
                             utils.lsb(message_length),
                             utils.msb(message_length)])
        if session_id:
            message.append(utils.lsb(session_id))
            message.append(utils.msb(session_id))
            message.append(utils.lsb(request_nr))
            message.append(utils.msb(request_nr))

        if data:
            for byte in data:
                if isinstance(byte, int):
                    message.append(byte)
                elif isinstance(byte, str):
                    message.append(ord(byte))
                else:
                    raise TypeError("Data does not contain int or str: %s is %s" % (str(byte), type(byte)))

        checksum = crc.crc16(message)
        message.append(utils.lsb(checksum))
        message.append(utils.msb(checksum))

        message.insert(0, consts.C3_MESSAGE_START)
        message.append(consts.C3_MESSAGE_END)
        return message

    def _send(self, command: consts.Command, data=None) -> int:
        message = self._construct_message(self._session_id, self._request_nr, command, data)

        self.log.debug("Sending: %s", message.hex())

        bytes_written = self._sock.send(message)
        self._request_nr = self._request_nr + 1
        return bytes_written

    def _receive(self) -> tuple[bytearray, int, int]:
        # Get the first 5 bytes
        self._sock.settimeout(self.receive_timeout)

        header = bytes()
        for _ in range(self.receive_retries):
            try:
                header = self._sock.recv(5)
                if len(header) == 5:
                    break
            except socket.timeout:
                pass

        if len(header) == 5:
            self.log.debug("Received header: %s", header.hex())

            message = bytearray()
            received_command, data_size, protocol_version = self._get_message_header(header)
            # Get the optional message data, checksum (2 bytes) and end marker (1 byte)
            payload = self._sock.recv(data_size + 3)
            if data_size > 0:
                # Process message in case data available
                self.log.debug("Receiving payload (data size %d): %s", data_size, payload.hex())
                message = self._get_message(header + payload)

            if len(message) != data_size:
                raise ValueError(f"Length of received message ({len(message)}) doesn't match specified ({data_size})")

            if received_command == consts.C3_REPLY_OK:
                pass
            elif received_command == consts.C3_REPLY_ERROR:
                error = utils.byte_to_signed_int(message[-1])
                raise ConnectionError(
                    f"Error {error} received in reply: {consts.Errors[error] if error in consts.Errors else 'Unknown'}")
        else:
            raise ConnectionError(f"Invalid response header received; expected 5 bytes, received {header}")

        return message, data_size, protocol_version

    def _send_receive(self, command: consts.Command, data=None) -> tuple[bytearray, int]:
        bytes_received = 0
        receive_data = bytearray()
        session_offset = 0

        try:
            bytes_written = self._send(command, data)
            if bytes_written > 0:
                receive_data, bytes_received, _ = self._receive()
                if not self._session_less and bytes_received > 2:
                    session_offset = 4
                    session_id = (receive_data[1] << 8) + receive_data[0]
                    # msg_seq = (receive_data[3] << 8) + receive_data[2]
                    if self._session_id != session_id:
                        raise ValueError("Data received with invalid session ID")
        except BrokenPipeError as ex:
            self._connected = False
            raise ConnectionError(f"Unexpected connection end: {ex}") from ex

        return receive_data[session_offset:], bytes_received-session_offset

    def _initialize(self):
        if not self._initialized:
            try:
                params = self.get_device_param(["~SerialNumber", "FirmVer", "DeviceName", "LockCount", "AuxInCount",
                                                "AuxOutCount"])
                self._device_info.serial_number = params.get("~SerialNumber", self._device_info.serial_number)
                self._device_info.firmware_version = params.get("FirmVer", self._device_info.firmware_version)
                self._device_info.device_name = params.get("DeviceName", self._device_info.device_name)
                self._status.nr_of_locks = int(params.get("LockCount", self._status.nr_of_locks))
                self._status.nr_aux_in = int(params.get("AuxInCount", self._status.nr_aux_in))
                self._status.nr_aux_out = int(params.get("AuxOutCount", self._status.nr_aux_out))
                self._initialized = True
            except ConnectionError as ex:
                self.log.error("Connection to %s failed: %s", self._device_info.host, ex)
            except ValueError as ex:
                self.log.error("Retrieving configuration parameters from %s failed: %s",
                               self._device_info.host, ex)

    def is_connected(self) -> bool:
        # try:
        #    # this will try to read bytes without blocking and also without removing them from buffer (peek only)
        #    data = self._sock.recv(1, socket.MSG_DONTWAIT | socket.MSG_PEEK)
        #    if len(data) == 0:
        #        return True
        # except BlockingIOError:
        #    return True  # socket is open and reading from it would block
        # except ConnectionResetError:
        #    return False  # socket was closed for some other reason
        # except Exception as e:
        #    return False
        return self._sock is not None and self._connected

    @classmethod
    def _parse_kv_from_message(cls, message: bytes) -> dict:
        kv_pairs = {}

        message_str = message.decode(encoding='ascii', errors='ignore')
        pattern = re.compile(r"([\w~]+)=([^,\t]+)")
        for (param_name, param_value) in re.findall(pattern, message_str):
            kv_pairs[param_name] = param_value

        return kv_pairs

    def __repr__(self):
        return "\r\n".join([
            f"- Host: {self.host} @ {self.port}",
            f"- Device: {self.device_name} (sn: {self.serial_number})",
            f"- Firmware version: {self.firmware_version}"
        ])

    def log_level(self, level: int):
        self.log.setLevel(level)

    @property
    def host(self) -> str:
        return self._device_info.host

    @host.setter
    def host(self, host: str):
        if not self.is_connected():
            self._device_info.host = host
        else:
            raise ConnectionError("Cannot set host when C3 is connected. Disconnect first.")

    @property
    def port(self) -> int:
        return self._device_info.port

    @port.setter
    def port(self, port: int):
        if not self.is_connected():
            self._device_info.port = port
        else:
            raise ConnectionError("Cannot set port when C3 is connected. Disconnect first.")

    @property
    def mac(self) -> str:
        return self._device_info.mac or '?'

    @property
    def serial_number(self) -> str:
        return self._device_info.serial_number or '?'

    @property
    def device_name(self) -> str:
        return self._device_info.device_name or '?'

    @property
    def firmware_version(self) -> str:
        return self._device_info.firmware_version or '?'

    @property
    def nr_of_locks(self) -> int:
        return self._status.nr_of_locks or 0

    @property
    def nr_aux_in(self) -> int:
        return self._status.nr_aux_in or 0

    @property
    def nr_aux_out(self) -> int:
        return self._status.nr_aux_out or 0

    @classmethod
    def discover(cls, interface_address: str = None, timeout: int = 2) -> list[C3]:
        """Scan on all local network interface, or the provided interface, for C3 panels."""
        devices = []
        message = cls._construct_message(None, None, consts.Command.DISCOVER, consts.C3_DISCOVERY_MESSAGE)

        if interface_address:
            ip_addresses = [interface_address]
        else:
            interfaces = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET)
            ip_addresses = [ip[-1][0] for ip in interfaces]
        for ip_address in ip_addresses:
            cls.log.debug("Discover on %s", ip_address)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            sock.bind((ip_address, 0))
            sock.sendto(message, ("255.255.255.255", consts.C3_PORT_BROADCAST))

            while True:
                try:
                    payload = sock.recv(64*1024)
                except socket.timeout:
                    break

                if payload:
                    received_command, data_size, _ = cls._get_message_header(payload)
                    if received_command == consts.C3_REPLY_OK:
                        # Get the message data and signature
                        message = cls._get_message(payload)

                        if len(message) != data_size:
                            raise ValueError(
                                "Length of received message (%d) does not match specified size (%d)" % (len(message),
                                                                                                        data_size))
                        data = cls._parse_kv_from_message(message)
                        devices.append(C3(C3DeviceInfo(
                            host=data.get("IP"),
                            mac=data.get("MAC"),
                            serial_number=data.get("SN"),
                            device_name=data.get("Device"),
                            firmware_version=data.get("Ver")
                        )))
            sock.close()

        return devices

    def connect(self, password: Optional[str] = None) -> bool:
        """Connect to the C3 panel on the host/port provided in the constructor."""
        self._connected = False
        self._session_id = 0xFEFE
        self._request_nr: -258

        data = None
        if password:
            data = bytearray(password.encode('ascii'))

        # Recreate a socket when it has been removed in disconnect method because of an error
        if self._sock is None:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self._sock.connect((self._device_info.host, self._device_info.port))
        except socket.error as ex:
            self.log.error("Error while opening socket: %s", str(ex))
            self._sock = None

        if self._sock is not None:
            # Attempt to connect to panel with session initiation command
            try:
                bytes_written = self._send(consts.Command.CONNECT_SESSION, data)
                if bytes_written > 0:
                    receive_data, bytes_received, protocol_version = self._receive()
                    if bytes_received > 2:
                        self._session_id = (receive_data[1] << 8) + receive_data[0]
                        self.log.debug("Connected with Session ID %04x", self._session_id)
                        self._session_less = False
                        self._protocol_version = protocol_version
                        self._connected = True
            except ConnectionError as ex:
                self.log.debug("Connection attempt with session to %s failed: %s", self._device_info.host, ex)
            except ValueError as ex:
                self.log.error("Reply from %s failed: %s", self._device_info.host, ex)

            # Alternatively attempt to connect to panel without session initiation
            if not self._connected:
                try:
                    self._session_id = None
                    bytes_written = self._send(consts.Command.CONNECT_SESSION_LESS, data)
                    if bytes_written > 0:
                        _, _, protocol_version = self._receive()
                        self.log.debug("Connected without session")
                        self._session_less = True
                        self._protocol_version = protocol_version
                        self._connected = True
                except ConnectionError as ex:
                    self.log.debug("Connection attempt without session to %s failed: %s",
                                   self._device_info.host, ex)
                except ValueError as ex:
                    self.log.error("Reply from %s failed: %s", self._device_info.host, ex)

        if self._connected:
            self._initialize()

        return self._connected

    def disconnect(self):
        """Disconnect from C3 panel and end session."""
        if self.is_connected():
            try:
                self._send_receive(consts.Command.DISCONNECT)
            except ConnectionError:
                # Disconnecting a broken connection should not create more trouble,
                # ignoring a ConnectionError for that reason.
                pass

            if self._sock is not None:
                try:
                    self._sock.close()
                except socket.error as ex:
                    self.log.error("Error while closing socket: %s", str(ex))
                self._sock = None

        self._connected = False
        self._session_id = None
        self._request_nr: -258

    def get_device_param(self, request_parameters: list[str]) -> dict:
        """Retrieve the requested device parameter values."""
        if self.is_connected():
            message, _ = self._send_receive(consts.Command.GETPARAM, ','.join(request_parameters))
            parameter_values = self._parse_kv_from_message(message)
        else:
            raise ConnectionError("No connection to C3 panel.")

        return parameter_values

    def _update_inout_status(self, logs: list[rtlog.RTLogRecord]):
        for log in logs:
            if isinstance(log, rtlog.DoorAlarmStatusRecord):
                for lock_nr in range(1, self.nr_of_locks+1):
                    self._set_lock_status(lock_nr, log.door_sensor_status(lock_nr), auto_close=False)

            elif isinstance(log, rtlog.EventRecord) and log.port_nr-1 in range(self.nr_of_locks):
                if log.event_type == consts.EventType.OPEN_AUX_OUTPUT:
                    self._set_aux_out_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=False)
                elif log.event_type == consts.EventType.CLOSE_AUX_OUTPUT:
                    self._set_aux_out_status(log.port_nr, consts.InOutStatus.CLOSED)

                elif log.event_type == consts.EventType.OPENED_ACCIDENT:
                    # Event feedback also expected via DoorAlarmStatusRecord, handling is probably double
                    self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=False)
                elif log.event_type == consts.EventType.DOOR_OPENED_CORRECT:
                    # Event feedback also expected via DoorAlarmStatusRecord, handling is probably double
                    self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=False)
                elif log.event_type == consts.EventType.DOOR_CLOSED_CORRECT:
                    # Event feedback also expected via DoorAlarmStatusRecord, handling is probably double
                    self._set_lock_status(log.port_nr, consts.InOutStatus.CLOSED)

                elif log.event_type == consts.EventType.AUX_INPUT_DISCONNECT:
                    self._set_aux_in_status(log.port_nr, consts.InOutStatus.OPEN)
                elif log.event_type == consts.EventType.AUX_INPUT_SHORT:
                    self._set_aux_in_status(log.port_nr, consts.InOutStatus.CLOSED)

                elif self.door_settings(log.port_nr).sensor_type == consts.DoorSensorType.NONE:
                    # When the door has no sensor, set the status based on the lock open/close events

                    # The lock drive time is used for automatic closing
                    lock_drive_time = self.door_settings(log.port_nr).lock_drive_time

                    if log.event_type == consts.EventType.NORMAL_PUNCH_OPEN:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    # PUNCH_NORMAL_OPEN_TZ
                    # Ignore "Punch during Normal Open Time Zone", door is already open
                    # FIRST_CARD_NORMAL_OPEN
                    # Ingore "First Card Normal Open (Punch Card)", door is already open
                    elif log.event_type == consts.EventType.MULTI_CARD_OPEN:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    elif log.event_type == consts.EventType.EMERGENCY_PASS_OPEN:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    elif log.event_type == consts.EventType.OPEN_NORMAL_OPEN_TZ:
                        # Not autoclosing, door is open during normal open time zone
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=False)
                    elif log.event_type == consts.EventType.REMOTE_OPENING:
                        # Remote closing command exected for closing, not setting auto-close
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=False)
                    elif log.event_type == consts.EventType.REMOTE_CLOSING:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.CLOSED)
                    elif log.event_type == consts.EventType.PRESS_FINGER_OPEN:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    elif log.event_type == consts.EventType.MULTI_CARD_OPEN_FP:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    # FP_NORMAL_OPEN_TZ
                    # Ingore "Press Fingerprint during Normal Open Time Zone", door is already open
                    elif log.event_type == consts.EventType.CARD_FP_OPEN:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    elif log.event_type == consts.EventType.FIRST_CARD_NORMAL_OPEN_FP:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    elif log.event_type == consts.EventType.FIRST_CARD_NORMAL_OPEN_CARD_FP:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    elif log.event_type == consts.EventType.DURESS_PASSWORD_OPEN:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    elif log.event_type == consts.EventType.DURESS_FP_OPEN:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    elif log.event_type == consts.EventType.EXIT_BUTTON_OPEN:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    elif log.event_type == consts.EventType.MULTI_CARD_OPEN_CARD_FP:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)
                    elif log.event_type == consts.EventType.NORMAL_OPEN_TZ_OVER:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.CLOSED)
                    elif log.event_type == consts.EventType.REMOTE_NORMAL_OPEN:
                        # Changes door to normal open, so open until normal open time ends (NORMAL_OPEN_TZ_OVER)
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=False)
                    elif log.event_type == consts.EventType.DOOR_OPEN_BY_SUPERUSER:
                        self._set_lock_status(log.port_nr, consts.InOutStatus.OPEN, auto_close=lock_drive_time)

    def get_rt_log(self) -> list[rtlog.EventRecord | rtlog.DoorAlarmStatusRecord]:
        """Retrieve the latest event or alarm records."""
        records = []

        if self.is_connected():
            message, message_length = self._send_receive(self._rtlog_command)
            if message_length:
                if self._rtlog_command == consts.Command.RTLOG_BINARY:
                    # One RT log is 16 bytes
                    # Ensure the array is not empty and a multiple of 16
                    if message_length % 16 == 0:
                        logs_messages = [message[i:i+16] for i in range(0, message_length, 16)]
                        for log_message in logs_messages:
                            self.log.debug("Received RT binary log: %s", log_message.hex())
                            records.append(rtlog.factory(log_message))
                    else:
                        # The panel firmware does not support binary mode
                        self.log.debug("Transition RT log mode to key/value")
                        self._rtlog_command = consts.Command.RTLOG_KEYVALUE
                elif self._rtlog_command == consts.Command.RTLOG_KEYVALUE:
                    kv_pairs = self._parse_kv_from_message(message)
                    self.log.debug("Received RT k/v log (%d): %s", len(kv_pairs), kv_pairs)
                    if len(kv_pairs) > 0:
                        records.append(rtlog.factory(kv_pairs))
                else:
                    raise NotImplementedError(f"The requested RT log command {self._rtlog_command} is not supported")
        else:
            raise ConnectionError("No connection to C3 panel.")

        self._update_inout_status(records)

        return records

    def _set_lock_status(self, door_nr: int, status: consts.InOutStatus, auto_close: bool | int = False) -> None:
        """Set the specified door lock status and optionally performs automatic close after specified timeout."""

        # Update the status only when status is more specific than unknown, or when no status is recorded at all
        if not status == consts.InOutStatus.UNKNOWN or door_nr not in self._status.lock_status:
            self._status.lock_status[door_nr] = status

        if status == consts.InOutStatus.OPEN and ((auto_close or 0) > 0):
            threading.Timer(auto_close, self._set_lock_status, [door_nr, consts.InOutStatus.CLOSED]).start()

    def _auto_close_lock(self, door_nr: int) -> None:
        """Set the specified door lock to closed.

        The C3 does not send an event to update the door lock activation status, only the sensor status.
        This means the lock (or alternatively the door) status is not updated for doors without sensor.
        This function is triggered by an automatic internal timer to set the lock state to closed."""
        self._status.lock_status[door_nr] = consts.InOutStatus.CLOSED

    def _set_aux_in_status(self, aux_nr: int, status: consts.InOutStatus) -> None:
        """Set the specified auxiliary input status"""

        # Update the status only when status is more specific than unknown, or when no status is recorded at all
        if not status == consts.InOutStatus.UNKNOWN or aux_nr not in self._status.aux_in_status:
            self._status.aux_in_status[aux_nr] = status

    def _set_aux_out_status(self, aux_nr: int, status: consts.InOutStatus, auto_close: bool | int = False) -> None:
        """Set the specified auxiliary output status and optionally performs automatic close after specified timeout."""

        # Update the status only when status is more specific than unknown, or when no status is recorded at all
        if not status == consts.InOutStatus.UNKNOWN or aux_nr not in self._status.aux_out_status:
            self._status.aux_out_status[aux_nr] = status

        if status == consts.InOutStatus.OPEN and ((auto_close or 0) > 0):
            threading.Timer(auto_close, self._set_aux_out_status, [aux_nr, consts.InOutStatus.CLOSED]).start()

    def _auto_close_aux_out(self, aux_nr: int) -> None:
        """Set the specified auxiliary output to closed.

        The C3 does not send an event when an auxiliary output closes after a certain duration.
        This function is triggered by an automatic internal timer to set the aux state to closed."""
        self._status.aux_out_status[aux_nr] = consts.InOutStatus.CLOSED

    def control_device(self, command: controldevice.ControlDeviceBase):
        """Send a control command to the panel."""
        if self.is_connected():
            self._send_receive(consts.Command.CONTROL, command.to_bytes())

            if isinstance(command, controldevice.ControlDeviceOutput):
                if command.operation == consts.ControlOperation.OUTPUT and command.duration < 255:
                    if command.address == consts.ControlOutputAddress.DOOR_OUTPUT and \
                            self.door_settings(command.output_number).sensor_type == consts.DoorSensorType.NONE:
                        threading.Timer(command.duration, self._auto_close_lock, [command.output_number]).start()
                    if command.address == consts.ControlOutputAddress.AUX_OUTPUT:
                        threading.Timer(command.duration, self._auto_close_aux_out, [command.output_number]).start()
        else:
            raise ConnectionError("No connection to C3 panel.")

    def door_settings(self, door_nr: int) -> C3DoorSettings:
        """Returns the settings of the door as configured on the panel"""
        if door_nr in self._status.door_settings:
            return self._status.door_settings[door_nr]
        elif not self._status.door_settings:
            for door_idx in range(self._status.nr_of_locks):
                door_prefix = f"Door{door_idx+1}"
                param_values = self.get_device_param(
                    [door_prefix + p for p in ["SensorType", "Drivertime", "Detectortime"]])
                if param_values:
                    self._status.door_settings[door_idx+1] = C3DoorSettings(
                        sensor_type=consts.DoorSensorType(int(param_values.get(door_prefix + "SensorType"))),
                        lock_drive_time=int(param_values.get(door_prefix + "Drivertime")),
                        door_alarm_timeout=int(param_values.get(door_prefix + "Detectortime")))

            return self._status.door_settings[door_nr]
        else:
            raise ValueError("Invalid door number specified (%d), 1-%d supported", door_nr, self._status.nr_of_locks)

    def lock_status(self, door_nr: int) -> consts.InOutStatus:
        """Returns the (cached) door open/close status.
        Requires a preceding call to get_rt_log to update to the latest status."""
        return self._status.lock_status[door_nr] if door_nr in self._status.lock_status else \
            consts.InOutStatus.UNKNOWN

    def aux_in_status(self, aux_nr: int) -> consts.InOutStatus:
        """Returns the (cached) auxiliary input short/disconnect status.
        Requires a preceding call to get_rt_log to update to the latest status."""
        return self._status.aux_in_status[aux_nr] if aux_nr in self._status.aux_in_status else \
            consts.InOutStatus.UNKNOWN

    def aux_out_status(self, aux_nr: int) -> consts.InOutStatus:
        """Returns the (cached) auxiliary output open/close status.
        Requires a preceding call to get_rt_log to update to the latest status."""
        return self._status.aux_out_status[aux_nr] if aux_nr in self._status.aux_out_status else \
            consts.InOutStatus.UNKNOWN

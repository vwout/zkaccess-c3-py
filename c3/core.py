from __future__ import annotations

import logging
import re
import socket
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional

# import consts
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
class C3PanelStatus:
    """C3 panel peripheral status"""
    nr_of_locks: int = 0
    nr_aux_in: int = 0
    nr_aux_out: int = 0
    lock_status: Dict[int, consts.InOutStatus] = field(default_factory=dict)
    aux_in_status: Dict[int, consts.InOutStatus] = field(default_factory=dict)
    aux_out_status: Dict[int, consts.InOutStatus] = field(default_factory=dict)


class C3:
    log = logging.getLogger("C3")
    log.setLevel(logging.ERROR)

    def __init__(self, host: [str | C3DeviceInfo], port: int = consts.C3_PORT_DEFAULT) -> None:
        self._sock: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(2)
        self._connected: bool = False
        self._session_less = False
        self._protocol_version = None
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
                data_size = data[3] + (data[4] * 255)
            else:
                raise ValueError("Received reply does not start with start token")
        else:
            raise ValueError("Received reply of unsufficient length (%d)", len(data))

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
                raise ValueError("Payload checksum is invalid: %x%x expected %x%x" %
                                 (data[-3], data[-2], utils.lsb(checksum), utils.msb(checksum)))
        else:
            raise ValueError("Payload does not include message end marker (%s)" % data[-1])

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
        header = self._sock.recv(5)
        self.log.debug("Receiving header: %s", header.hex())

        message = bytearray()
        received_command, data_size, protocol_version = self._get_message_header(header)
        # Get the optional message data, checksum and end marker
        payload = self._sock.recv(data_size + 3)
        if data_size > 0:
            # Process message in case data available
            self.log.debug("Receiving payload: %s", payload.hex())
            message = self._get_message(header + payload)

        if len(message) != data_size:
            raise ValueError(f"Length of received message ({len(message)}) does not match specified size ({data_size})")

        if received_command == consts.C3_REPLY_OK:
            pass
        elif received_command == consts.C3_REPLY_ERROR:
            error = utils.byte_to_signed_int(message[-1])
            raise ConnectionError(
                f"Error {error} received in reply: {consts.Errors[error] if error in consts.Errors else 'Unknown'}")
        else:
            data_size = 0

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
        return self._connected

    @classmethod
    def _parse_kv_from_message(cls, message: bytes) -> dict:
        kv_pairs = {}

        message_str = message.decode(encoding='ascii', errors='ignore')
        pattern = re.compile(r"([\w~]+)=([^,]+)")
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

        # Attempt to connect to panel with session initiation command
        try:
            self._sock.connect((self._device_info.host, self._device_info.port))
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
                self._sock.connect((self._device_info.host, self._device_info.port))
                bytes_written = self._send(consts.Command.CONNECT_SESSION_LESS, data)
                if bytes_written > 0:
                    _, _, protocol_version = self._receive()
                    self.log.debug("Connected without session")
                    self._session_less = True
                    self._protocol_version = protocol_version
                    self._connected = True
            except ConnectionError as ex:
                self.log.debug("Connection attempt without session to %s failed: %s", self._device_info.host, ex)
            except ValueError as ex:
                self.log.error("Reply from %s failed: %s", self._device_info.host, ex)

        if self._connected:
            try:
                params = self.get_device_param(["~SerialNumber", "LockCount", "AuxInCount", "AuxOutCount"])
                self._device_info.serial_number = params.get("~SerialNumber", self._device_info.serial_number)
                self._status.nr_of_locks = int(params.get("LockCount", self._status.nr_of_locks))
                self._status.nr_aux_in = int(params.get("AuxInCount", self._status.nr_aux_in))
                self._status.nr_aux_out = int(params.get("AuxOutCount", self._status.nr_aux_out))
            except ConnectionError as ex:
                self.log.error("Connection to %s failed: %s", self._device_info.host, ex)
            except ValueError as ex:
                self.log.error("Retrieving configuration parameters from %s failed: %s", self._device_info.host, ex)

        return self._connected

    def disconnect(self):
        """Disconnect from C3 panel and end session."""
        if self.is_connected():
            self._send_receive(consts.Command.DISCONNECT)
            self._sock.close()

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
                for lock_nr in range(1, self._status.nr_of_locks+1):
                    self._status.lock_status[lock_nr] = log.door_sensor_status(lock_nr)
            elif isinstance(log, rtlog.EventRecord):
                if log.event_type == consts.EventType.OPEN_AUX_OUTPUT:
                    self._status.aux_out_status[log.door_id] = consts.InOutStatus.OPEN
                elif log.event_type == consts.EventType.CLOSE_AUX_OUTPUT:
                    self._status.aux_out_status[log.door_id] = consts.InOutStatus.CLOSED
                elif log.event_type == consts.EventType.AUX_INPUT_DISCONNECT:
                    self._status.aux_in_status[log.door_id] = consts.InOutStatus.OPEN
                elif log.event_type == consts.EventType.AUX_INPUT_SHORT:
                    self._status.aux_in_status[log.door_id] = consts.InOutStatus.CLOSED

    def get_rt_log(self) -> list[rtlog.EventRecord | rtlog.DoorAlarmStatusRecord]:
        """Retrieve the latest event or alarm records."""
        records = []

        if self.is_connected():
            message, message_length = self._send_receive(consts.Command.RTLOG)

            # One RT log is 16 bytes
            # Ensure the array is not empty and a multiple of 16
            if message_length % 16 == 0:
                logs_messages = [message[i:i+16] for i in range(0, message_length, 16)]
                for log_message in logs_messages:
                    self.log.debug("Received RT Log: %s", log_message.hex())
                    records.append(rtlog.factory(log_message))
            else:
                if self._protocol_version == 2:
                    # Protocol version (?) 2 response with a different message structure
                    # For now ignoring all data but last 16 bytes
                    self.log.debug("Received too many bytes, only using tail: %s", message.hex())
                    records.append(rtlog.factory(message[-16:]))
                else:
                    raise ValueError("Received RT Log(s) size is not a multiple of 16: %d" % message_length)
        else:
            raise ConnectionError("No connection to C3 panel.")

        self._update_inout_status(records)

        return records

    def _auto_close_aux_out(self, aux_nr: int) -> None:
        """Set the specified auxiliary output to closed.

        The C3 does not send an event when an auxiliary output closes after a certain duration.
        This function is trigger by an automatic internal timer to set the internal state to closed."""
        self._status.aux_out_status[aux_nr] = consts.InOutStatus.CLOSED

    def control_device(self, command: controldevice.ControlDeviceBase):
        """Send a control command to the panel."""
        if self.is_connected():
            self._send_receive(consts.Command.CONTROL, command.to_bytes())

            if isinstance(command, controldevice.ControlDeviceOutput):
                if command.operation == consts.ControlOperation.OUTPUT and \
                        command.address == consts.ControlOutputAddress.AUX_OUTPUT and \
                        command.duration < 255:
                    threading.Timer(command.duration, self._auto_close_aux_out, [command.output_number]).start()
        else:
            raise ConnectionError("No connection to C3 panel.")

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

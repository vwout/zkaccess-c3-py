from __future__ import annotations
import re
import logging
import socket
from typing import Optional
from c3 import consts
from c3 import crc
from c3 import utils
from c3 import rtlog
from c3 import controldevice


class C3:
    log = logging.getLogger("C3")
    log.setLevel(logging.ERROR)

    def __init__(self, host: str, port: int = None, mac: str = None, sn: str = None, device: str = None,
                 firmware_version: str = None):
        self._sock: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(2)
        self._connected = False
        self._session_id: int = 0
        self._request_nr: int = 0
        self._nr_of_locks = 0
        self._nr_aux_in = 0
        self._nr_aux_out = 0
        self._host = host
        self._port = port or consts.C3_PORT_DEFAULT
        self._mac = mac
        self._sn = sn
        self._device = device
        self._firmware_version = firmware_version

    @classmethod
    def _get_message_header(cls, data: [bytes or bytearray]) -> tuple[[int or None], int]:
        command = None
        data_size = 0

        if len(data) >= 5:
            if data[0] == consts.C3_MESSAGE_START:  # and data[1] == consts.C3_PROTOCOL_VERSION:
                command = data[2]
                data_size = data[3] + (data[4] * 255)

        return command, data_size

    @classmethod
    def _get_message(cls, data: [bytes or bytearray]) -> bytearray:
        if data[-1] == consts.C3_MESSAGE_END:
            # Get the message payload, without start, crc and end bytes
            checksum = crc.crc16(data[1:-3])

            if utils.lsb(checksum) == data[-3] or utils.msb(checksum) == data[-2]:
                # Return all data without header (leading) and crc (trailing)
                message = bytearray(data[5:-3])
            else:
                raise ValueError("Payload checksum is invalid: %s expected %x" % (data[-3:-2].hex(), checksum))
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
        if session_id and request_nr:
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
        message = self._construct_message(self._session_id or 0, self._request_nr or 0, command, data)

        self.log.debug("Sending: %s", message.hex())

        bytes_written = self._sock.send(message)
        self._request_nr = self._request_nr + 1
        return bytes_written

    def _receive(self) -> tuple[bytearray, int]:
        # Get the first 5 bytes
        header = self._sock.recv(5)
        self.log.debug(f"Receiving header: {header.hex()}")

        received_command, data_size = self._get_message_header(header)
        # Get the message data and signature
        payload = self._sock.recv(data_size + 3)
        self.log.debug(f"Receiving payload: {payload.hex()}", )
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

        return message, data_size

    def _send_receive(self, command: consts.Command, data=None) -> tuple[bytearray, int]:
        bytes_received = 0
        receive_data = bytearray()

        bytes_written = self._send(command, data)
        if bytes_written > 0:
            receive_data, bytes_received = self._receive()
            if bytes_received > 2:
                session_id = (receive_data[1] << 8) + receive_data[0]
                # msg_seq = (receive_data[3] << 8) + receive_data[2]
                if self._session_id != session_id:
                    raise ValueError("Data received with invalid session ID")

        return receive_data[4:], bytes_received-4

    def _is_connected(self) -> bool:
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
        kv = {}

        message_str = message.decode(encoding='ascii', errors='ignore')
        pattern = re.compile(r"([\w~]+)=([^,]+)")
        for (k, v) in re.findall(pattern, message_str):
            kv[k] = v

        return kv

    def __repr__(self):
        return "\r\n".join([
            f"- Host: {self.host} @ {self.port}",
            f"- Device: {self.device} (sn: {self.sn})",
            f"- Firmware version: {self.firmware_version}"
        ])

    def log_level(self, level: int):
        self.log.setLevel(level)

    @property
    def host(self) -> str:
        return self._host

    @host.setter
    def host(self, host: str):
        if not self._is_connected():
            self._host = host
        else:
            raise ConnectionError("Cannot set host when C3 is connected. Disconnect first.")

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, port: int):
        if not self._is_connected():
            self._port = port
        else:
            raise ConnectionError("Cannot set port when C3 is connected. Disconnect first.")

    @property
    def mac(self) -> str:
        return self._mac or '?'

    @property
    def sn(self) -> str:
        return self._sn or '?'

    @property
    def device(self) -> str:
        return self._device or '?'

    @property
    def firmware_version(self) -> str:
        return self._firmware_version or '?'

    @property
    def nr_of_locks(self) -> int:
        return self._nr_of_locks or 0

    @property
    def nr_aux_in(self) -> int:
        return self._nr_aux_in or 0

    @property
    def nr_aux_out(self) -> int:
        return self._nr_aux_out or 0

    @classmethod
    def discover(cls, interface_address: str = None, timeout: int = 2) -> list[C3]:
        """Scan on all local network interface, or the provided interface, for C3 panels."""
        devices = []
        message = cls._construct_message(None, None, consts.Command.DISCOVER, consts.C3_DISCOVERY_MESSAGE)

        if interface_address:
            ips = [interface_address]
        else:
            interfaces = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET)
            ips = [ip[-1][0] for ip in interfaces]
        for ip in ips:
            cls.log.debug(f"Discover on {ip}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            sock.bind((ip, 0))
            sock.sendto(message, ("255.255.255.255", consts.C3_PORT_BROADCAST))

            while True:
                try:
                    payload = sock.recv(64*1024)
                except socket.timeout:
                    break

                if payload:
                    received_command, data_size = cls._get_message_header(payload)
                    if received_command == consts.C3_REPLY_OK:
                        # Get the message data and signature
                        message = cls._get_message(payload)

                        if len(message) != data_size:
                            raise ValueError(
                                "Length of received message (%d) does not match specified size (%d)" % (len(message),
                                                                                                        data_size))
                        data = cls._parse_kv_from_message(message)
                        devices.append(C3(
                            host=data.get("IP"),
                            mac=data.get("MAC"),
                            sn=data.get("SN"),
                            device=data.get("Device"),
                            firmware_version=data.get("Ver")
                        ))
            sock.close()

        return devices

    def connect(self) -> bool:
        """Connect to the C3 panel on the host/port provided in the constructor."""
        self._connected = False
        self._session_id = 0

        try:
            self._sock.connect((self._host, self._port))
            bytes_written = self._send(consts.Command.CONNECT)
            if bytes_written > 0:
                receive_data, bytes_received = self._receive()
                if bytes_received > 2:
                    self._session_id = (receive_data[1] << 8) + receive_data[0]
                    self.log.debug("Connected with Session ID %x", self._session_id)
                    self._connected = True
        except Exception as e:
            self.log.error(f"Connection to {self._host} failed: {e}")

        if self._connected:
            params = self.get_device_param(["~SerialNumber", "LockCount", "AuxInCount", "AuxOutCount"])
            self._sn = int(params.get("~SerialNumber", self._sn))
            self._nr_of_locks = int(params.get("LockCount", self._nr_of_locks))
            self._nr_aux_in = int(params.get("AuxInCount", self._nr_aux_in))
            self._nr_aux_out = int(params.get("AuxOutCount", self._nr_aux_out))

        return self._connected

    def disconnect(self):
        """Disconnect from C3 panel and end session."""
        if self._is_connected():
            self._send_receive(consts.Command.DISCONNECT)
            self._sock.close()

        self._connected = False
        self._session_id = 0
        self._request_nr = 0

    def get_device_param(self, request_parameters: list[str]) -> dict:
        """Retrieve the requested device parameter values."""
        if self._is_connected():
            message, _ = self._send_receive(consts.Command.GETPARAM, ','.join(request_parameters))
            parameter_values = self._parse_kv_from_message(message)
        else:
            raise ConnectionError("No connection to C3 panel.")

        return parameter_values

    def get_rt_log(self) -> list[rtlog.RTLogRecord]:
        """Retrieve the latest event or alarm records."""
        records = []

        if self._is_connected():
            message, message_length = self._send_receive(consts.Command.RTLOG)

            # One RT log is 16 bytes
            # Ensure the array is not empty and a multiple of 16
            if message_length % 16 == 0:
                logs_messages = [message[i:i+16] for i in range(0, message_length, 16)]
                for log_message in logs_messages:
                    self.log.debug("Received RT Log: %s", log_message.hex())
                    if log_message[10] == consts.EventType.DOOR_ALARM_STATUS:
                        records.append(rtlog.DoorAlarmStatusRecord.from_bytes(log_message))
                    else:
                        records.append(rtlog.EventRecord.from_bytes(log_message))
            else:
                raise ValueError("Received RT Log(s) size is not a multiple of 16: %d" % message_length)
        else:
            raise ConnectionError("No connection to C3 panel.")

        return records

    def control_device(self, control_command: controldevice.ControlDeviceBase):
        """Send a control command to the panel."""
        if self._is_connected():
            self._send_receive(consts.Command.CONTROL, control_command.to_bytes())
        else:
            raise ConnectionError("No connection to C3 panel.")

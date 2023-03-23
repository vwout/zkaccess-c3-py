import re
import socket
import logging
from c3 import consts
from c3 import crc
from c3 import utils
from c3 import rtlog
from c3 import controldevice


class C3:
    log = logging.getLogger("C3")
    log.setLevel(logging.ERROR)

    def __init__(self):
        self._sock: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(2)
        self._connected = False
        self._session_id: int = 0
        self._request_nr: int = 0
        self._nr_of_locks = 0
        self._nr_aux_in = 0
        self._nr_aux_out = 0

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
    def _construct_message(cls, session_id: int, request_nr: int, command: consts.CommandStruct, data=None) -> bytes:
        message_length = len(data or []) + (4 if (session_id and request_nr) else 0)
        message = bytearray([consts.C3_PROTOCOL_VERSION,
                             command.request or 0x00,
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

    def _send(self, command: consts.CommandStruct, data=None) -> int:
        message = self._construct_message(self._session_id or 0, self._request_nr or 0, command, data)

        self.log.debug("Sending: %s", message.hex(' ', 1))

        bytes_written = self._sock.send(message)
        self._request_nr = self._request_nr + 1
        return bytes_written

    def _receive(self, expected_command: consts.CommandStruct) -> tuple[bytearray, int]:
        message = bytearray()

        # Get the first 5 bytes
        header = self._sock.recv(5)
        self.log.debug("Receiving header: %s", header.hex(' ', 1))

        received_command, data_size = self._get_message_header(header)
        if received_command == expected_command.reply:
            # Get the message data and signature
            payload = self._sock.recv(data_size + 3)
            self.log.debug("Receiving payload: %s", payload.hex(' ', 1))
            message = self._get_message(header + payload)

            if len(message) != data_size:
                raise ValueError("Length of received message (%d) does not match specified size (%d)" % (len(message),
                                                                                                         data_size))
        else:
            data_size = 0

        return message, data_size

    def _send_receive(self, command: consts.CommandStruct, data=None) -> tuple[bytearray, int]:
        bytes_received = 0
        receive_data = bytearray()

        bytes_written = self._send(command, data)
        if bytes_written > 0:
            receive_data, bytes_received = self._receive(command)
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

    def log_level(self, level: int):
        self.log.setLevel(level)

    @property
    def nr_of_locks(self) -> int:
        return self._nr_of_locks

    @property
    def nr_aux_in(self) -> int:
        return self._nr_aux_in

    @property
    def nr_aux_out(self) -> int:
        return self._nr_aux_out

    @classmethod
    def discover(cls, interface_address: str = None, timeout: int = 2) -> list[dict]:
        devices = []
        message = cls._construct_message(None, None, consts.C3_COMMAND_DISCOVER, consts.C3_DISCOVERY_MESSAGE)

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
            sock.sendto(message, ("255.255.255.255", 65535))

            while True:
                try:
                    payload = sock.recv(64*1024)
                except socket.timeout:
                    break

                if payload:
                    received_command, data_size = cls._get_message_header(payload)
                    if received_command == consts.C3_COMMAND_DISCOVER.reply:
                        # Get the message data and signature
                        message = cls._get_message(payload)

                        if len(message) != data_size:
                            raise ValueError(
                                "Length of received message (%d) does not match specified size (%d)" % (len(message),
                                                                                                        data_size))
                        devices.append(cls._parse_kv_from_message(message))
            sock.close()

        return devices

    def connect(self, host: str, port: int = consts.C3_PORT_DEFAULT) -> bool:
        self._connected = False
        self._session_id = 0

        self._sock.connect((host, port))
        bytes_written = self._send(consts.C3_COMMAND_CONNECT)
        if bytes_written > 0:
            receive_data, bytes_received = self._receive(consts.C3_COMMAND_CONNECT)
            if bytes_received > 2:
                self._session_id = (receive_data[1] << 8) + receive_data[0]
                self.log.debug("Connected with Session ID %x", self._session_id)
                self._connected = True

        if self._connected:
            params = self.get_device_param(["LockCount", "AuxInCount", "AuxOutCount"])
            self._nr_of_locks = int(params.get("LockCount", self._nr_of_locks))
            self._nr_aux_in = int(params.get("AuxInCount", self._nr_aux_in))
            self._nr_aux_out = int(params.get("AuxOutCount", self._nr_aux_out))

        return self._connected

    def disconnect(self):
        self._send_receive(consts.C3_COMMAND_DISCONNECT)
        self._sock.close()

        self._connected = False
        self._session_id = 0
        self._request_nr = 0

    def get_device_param(self, request_parameters: list[str]) -> dict:
        if self._is_connected():
            message, _ = self._send_receive(consts.C3_COMMAND_GETPARAM, ','.join(request_parameters))
            parameter_values = self._parse_kv_from_message(message)
        else:
            raise ConnectionError("No connection to C3 panel.")

        return parameter_values

    def get_rt_log(self) -> list[rtlog.RTLogRecord]:
        records = []

        if self._is_connected():
            message, message_length = self._send_receive(consts.C3_COMMAND_RTLOG)

            # One RT log is 16 bytes
            # Ensure the array is not empty and a multiple of 16
            if message_length % 16 == 0:
                logs_messages = [message[i:i+16] for i in range(0, message_length, 16)]
                for log_message in logs_messages:
                    self.log.debug("Received RT Log: %s", log_message.hex(" "))
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
        if self._is_connected():
            self._send_receive(consts.C3_COMMAND_CONTROL, control_command.to_bytes())
        else:
            raise ConnectionError("No connection to C3 panel.")

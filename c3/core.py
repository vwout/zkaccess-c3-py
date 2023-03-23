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
        self.session_id: int = 0
        self.request_nr: int = 0

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
        message = bytearray()
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

    def _send(self, command: consts.CommandStruct, data=None) -> int:
        message_length = 0x04 + len(data or [])
        message = bytearray([consts.C3_PROTOCOL_VERSION,
                             command.request or 0x00,
                             utils.lsb(message_length),
                             utils.msb(message_length),
                             utils.lsb(self.session_id or 0),
                             utils.msb(self.session_id or 0),
                             utils.lsb(self.request_nr),
                             utils.msb(self.request_nr)])

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

        self.log.debug("Sending: %s", message.hex(' ', 1))

        bytes_written = self._sock.send(message)
        self.request_nr = self.request_nr + 1
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
                if self.session_id != session_id:
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

    def log_level(self, level: int):
        self.log.setLevel(level)

    @classmethod
    def discover(cls, interface_address: str = None, timeout: int = 2):
        devices = []

        data = consts.C3_DISCOVERY_MESSAGE
        message_length = len(data)
        message = bytearray([consts.C3_PROTOCOL_VERSION,
                             consts.C3_COMMAND_DISCOVER.request or 0x00,
                             utils.lsb(message_length),
                             utils.msb(message_length)])

        for byte in data:
            message.append(ord(byte))

        checksum = crc.crc16(message)
        message.append(utils.lsb(checksum))
        message.append(utils.msb(checksum))

        message.insert(0, consts.C3_MESSAGE_START)
        message.append(consts.C3_MESSAGE_END)

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
                    parameter_values = {}

                    received_command, data_size = cls._get_message_header(payload)
                    if received_command == consts.C3_COMMAND_DISCOVER.reply:
                        # Get the message data and signature
                        message = cls._get_message(payload)

                        if len(message) != data_size:
                            raise ValueError(
                                "Length of received message (%d) does not match specified size (%d)" % (len(message),
                                                                                                        data_size))
                        message_str = message.decode(encoding='ascii', errors='ignore')
                        pattern = re.compile(r"([\w~]+)=([^,]+)")
                        for (k, v) in re.findall(pattern, message_str):
                            parameter_values[k] = v

                        devices.append(parameter_values)
            sock.close()

        return devices

    def connect(self, host: str, port: int = consts.C3_PORT_DEFAULT) -> bool:
        self._connected = False
        self.session_id = 0

        self._sock.connect((host, port))
        bytes_written = self._send(consts.C3_COMMAND_CONNECT)
        if bytes_written > 0:
            receive_data, bytes_received = self._receive(consts.C3_COMMAND_CONNECT)
            if bytes_received > 2:
                self.session_id = (receive_data[1] << 8) + receive_data[0]
                self.log.debug("Connected with Session ID %x", self.session_id)
                self._connected = True

        return self._connected

    def disconnect(self):
        self._send_receive(consts.C3_COMMAND_DISCONNECT)
        self._sock.close()

        self._connected = False
        self.session_id = 0
        self.request_nr = 0

    def get_device_param(self, request_parameters: list[str]) -> dict:
        parameter_values = {}
        if self._is_connected():
            message, _ = self._send_receive(consts.C3_COMMAND_GETPARAM, ','.join(request_parameters))
            message_str = message.decode(encoding='ascii', errors='ignore')
            pattern = re.compile(r"([\w~]+)=(\w+)")
            for (k, v) in re.findall(pattern, message_str):
                parameter_values[k] = v
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

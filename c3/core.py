from c3 import consts
from c3 import crc
from c3 import utils
from c3 import rtlog
import re
import socket
import logging


class C3:
    def __init__(self):
        self._sock: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(2)
        self._connected = False
        self.session_id: int = None
        self.request_nr: int = 0
        self.log = logging.getLogger("C3")
        self.log.setLevel(logging.ERROR)

    @classmethod
    def _get_message_header(cls, data: [bytes or bytearray]) -> tuple[[int or None], int]:
        command = None
        data_size = 0

        if len(data) >= 5:
            if data[0] == consts.C3_MESSAGE_START: #and data[1] == consts.C3_PROTOCOL_VERSION:
                command = data[2]
                data_size = data[3] + (data[4] * 255)

        return command, data_size

    def _get_message(self, data: [bytes or bytearray]) -> bytearray:
        message = bytearray()
        if data[-1] == consts.C3_MESSAGE_END:
            # Get the message payload, without start, crc and end bytes
            checksum = crc.crc16(data[1:-3])

            if utils.lsb(checksum) == data[-3] or utils.msb(checksum) == data[-2]:
                # Return all data without header (leading) and crc (trailing)
                message = bytearray(data[5:-3])
            else:
                self.log.debug("Payload checksum is invalid: %s expected %x", data[-3:-2].hex(), checksum)
        else:
            self.log.debug("Payload does not include message end marker (%s)", data[-1])

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
            for b in data:
                if type(b) is int:
                    message.append(b)
                elif type(b) is str:
                    message.append(ord(b))
                else:
                    raise TypeError("Data does not contain int or str: %s is %s" % (str(b), type(b)))

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
                raise ValueError("Length of received message (%d) does not match specified size (%d)" % (len(message), data_size))
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
                #msg_seq = (receive_data[3] << 8) + receive_data[2]
                if self.session_id != session_id:
                    raise ValueError("Data received with invalid session ID")

        return receive_data[4:], bytes_received-4

    def _is_connected(self) -> bool:
        #try:
        #    # this will try to read bytes without blocking and also without removing them from buffer (peek only)
        #    data = self._sock.recv(1, socket.MSG_DONTWAIT | socket.MSG_PEEK)
        #    if len(data) == 0:
        #        return True
        #except BlockingIOError:
        #    return True  # socket is open and reading from it would block
        #except ConnectionResetError:
        #    return False  # socket was closed for some other reason
        #except Exception as e:
        #    return False
        return self._connected

    def log_level(self, level: int):
        self.log.setLevel(level)

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

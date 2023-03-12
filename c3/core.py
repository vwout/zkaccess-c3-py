import consts
import crc
import socket
import logging


class C3:
    def __init__(self):
        self._sock: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(2)
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

        return receive_data, bytes_received

        return response, bytes_received, receive_data

    def log_level(self, level: int):
        self.log.setLevel(level)

    def connect(self, host: str, port: int = consts.C3_PORT_DEFAULT) -> bool:
        connected = False

        self._sock.connect((host, port))
        receive_data, bytes_received = self._send_receive(consts.C3_COMMAND_CONNECT)
        if bytes_received > 2:
            self.session_id = (receive_data[1] << 8) + receive_data[0]
            self.log.debug("Connected with Session ID %x", self.session_id)
            connected = True
        else:
            self.session_id = 0

        return connected

    def disconnect(self):
        self._send_receive(consts.C3_COMMAND_DISCONNECT)
        self._sock.close()

        self.session_id = 0
        self.request_nr = 0

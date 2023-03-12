import consts
import crc
import socket
import utils


class C3:
    def __init__(self):
        self._sock: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(2)
        self.session_id: int = None
        self.request_nr: int = 0

    @classmethod
    def _get_message_header(cls, data: [bytes or bytearray]) -> tuple([int or None], int):
        command = None
        data_size = 0

        if len(data) >= 5:
            if data[0] == consts.C3_MESSAGE_START and data[1] ==  consts.C3_PROTOCOL_VERSION:
                command = data[3]
                data_size = data[4] + (data[5] * 255)

          return command, data_size

    @classmethod
    def _get_message(cls, data: [bytes or bytearray]) -> [bytearray or None]:
        message = None
        if data[:-1] == consts.C3_MESSAGE_END:
            # Get the message payload, without start, crc and end bytes
            message = bytearray(data[1:-3])
            checksum = crc.crc16(message)

            if utils.lsb(checksum) == data[:-3] and utils.msb(checksum) == data[:-2]:
                # Remove the header(4 bytes)
                del message[0:3]

        return message

    def _send(self, command: consts.CommandStruct, data = None) -> int:
        message_length = 0x04 + len(data or [])
        message = bytearray([consts.C3_PROTOCOL_VERSION,
                             command.request or 0x00,
                             utils.lsb(message_length),
                             utils.msb(message_length),
                             utils.lsb(self.session_id),
                             utils.msb(self.session_id),
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

        bytes_written = self._sock.send(message)
        self.request_nr = self.request_nr + 1
        return bytes_written

    def _receive(self, expected_command: consts.CommandStruct) -> [bytearray or None]:
        size = 0
        message = None

        # Get the first 5 bytes
        header = self._sock.recv(5)
        received_command, data_size = self._get_message_header(header)
        if received_command == expected_command.reply:
            # Get the message data and signature
            payload = self._sock.recv(data_size + 3)
            message = self._get_message(payload)

            if len(message) != data_size:
                raise ValueError("Length of received message (%d) does not match specified size (%d)" % (len(message), data_size))

        return size, message

    def _send_receive(self, command: consts.CommandStruct, data = None):
        bytes_received = 0
        receive_data = None
        response = None

        bytes_written = self._send(command, data)
        if bytes_written > 0:
            bytes_received, receive_data = self._receive(command)

        return response, bytes_received, receive_data

    def connect(self, host: str, port: int = consts.C3_PORT_DEFAULT):
        self._sock.connect((host, port))
        self._send_receive(consts.C3_COMMAND_CONNECT)

    def disconnect(self):
        self._send_receive(consts.C3_COMMAND_DISCONNECT)
        self._sock.close()

        self.session_id = None
        self.request_nr=  0

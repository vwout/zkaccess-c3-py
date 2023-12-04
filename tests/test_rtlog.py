from unittest import mock

from c3.core import C3
from c3.consts import VerificationMode
from c3.rtlog import EventRecord, DoorAlarmStatusRecord
from c3.utils import C3DateTime


def test_c3_rtlog_event_decode1():
    raw_data = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xc8, 0x01, 0x66, 0x02, 0x32, 0x8f, 0xae, 0x21])
    # assert 1501491250 == int.from_bytes(raw_data[12:16], byteorder="little") #11439922
    # assert 1501491250 == int.from_bytes(raw_data[12:16], byteorder="big") #3313582
    # assert 1501491250 == int.from_bytes(reversed(raw_data[12:16]), byteorder="little") # 3313582
    # assert 1501491250 == int.from_bytes(reversed(raw_data[12:16]), byteorder="big") #11439922
    record = EventRecord.from_bytes(raw_data)
    # assert C3DateTime.from_value(1501491250) == record.time_second
    assert C3DateTime(year=2017, month=7, day=31, hour=8, minute=54, second=10) == record.time_second
    assert not record.is_door_alarm()
    assert record.is_event()
    print(repr(record))


def test_c3_rtlog_event_decode2():
    raw_data = bytes([0x17, 0x30, 0x64, 0x12, 0xe2, 0xb1, 0x04, 0x00, 0x04, 0x01, 0x00, 0x00, 0x74, 0x2c, 0xaf, 0x21])
    record = EventRecord.from_bytes(raw_data)
    # assert C3DateTime.from_value(1501531508) == record.time_second
    assert not record.is_door_alarm()
    assert record.is_event()
    print(repr(record))


def test_c3_rtlog_decode_status1():
    raw_data = bytes([0x03, 0x00, 0x00, 0x00, 0x11, 0x00, 0x00, 0x00, 0x00, 0x01, 0xff, 0x00, 0xf2, 0x31, 0xb3, 0x21])
    record = DoorAlarmStatusRecord.from_bytes(raw_data)
    assert 0 < len(record.get_alarms(door_nr=None))
    assert record.has_alarm(1)
    assert not record.has_alarm(2)
    assert record.has_alarm(1, 1)
    assert record.has_alarm(1, 2)
    # assert not record.has_alarm(1, 3)
    assert False is record.door_is_open(1)
    assert None is record.door_is_open(3)
    assert record.is_door_alarm()
    assert not record.is_event()
    print(repr(record))


def test_c3_rtlog_decode_status2():
    raw_data = bytes([0x03, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x01, 0x01, 0xff, 0x00, 0xfc, 0x31, 0xb3, 0x21])
    record = DoorAlarmStatusRecord.from_bytes(raw_data)
    assert record.has_alarm(1)
    assert record.door_is_open(1)
    assert None is record.door_is_open(2)
    assert record.is_door_alarm()
    assert not record.is_event()
    print(repr(record))


def test_rtlog_unknown_verification_mode():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa00c80400"), bytes.fromhex("d805fefea30955"),
            bytes.fromhex("aa00c80400"), bytes.fromhex("d805000062e955")
        ]

        assert panel.connect() is True

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c81400"),
            bytes.fromhex("d805e8ff0200000011000000000bff00fa61fb2c38b255")]
        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], DoorAlarmStatusRecord)
        assert logs[0].verified == VerificationMode.CARD_WITH_PASSWORD

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c81400"),
            bytes.fromhex("d805e8ff02000000110007000007ff00fa61fb2c456855")]
        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert logs[0].verified == VerificationMode.OTHER


def test_rtlog_version2_response():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa02c90100"), bytes.fromhex("f357d955"),
            bytes.fromhex("aa02c80000"), bytes.fromhex("81fe55"),
            bytes.fromhex("aa02c84200"), bytes.fromhex("7e53657269616c4e756d6265723d4143"
                                                       "59543033323335333632372c4c6f636b"
                                                       "436f756e743d342c417578496e436f756"
                                                       "e743d342c4175784f7574436f756e743d"
                                                       "34599355"),
            # Not sure what the message structure of the response use protocol version (?) 02 is;
            # for now only the last 16 bytes are used
            bytes.fromhex("aa02c82400"), bytes.fromhex("02000000"
                                                       "32000000000000000000000000000000"
                                                       "0000000000000000c800ff0071c7d42d"
                                                       "4d3955"),
            bytes.fromhex("aa02c82400"), bytes.fromhex("02000000"
                                                       "32000000000000000000000000000000"
                                                       "0000000000000000c800ff006b13d52d"
                                                       "0b8955")
        ]

        assert panel.connect() is True

        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], DoorAlarmStatusRecord)

        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], DoorAlarmStatusRecord)

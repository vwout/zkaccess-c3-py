from unittest import mock
import time
import pytest

from c3 import rtlog
from c3.core import C3
from c3 import consts
from c3 import controldevice


def test_core_init():
    panel = C3('localhost')
    assert panel.nr_of_locks == 0
    assert panel.nr_aux_in == 0
    assert panel.nr_aux_out == 0
    assert panel.lock_status(1) == consts.InOutStatus.UNKNOWN
    assert panel.aux_in_status(1) == consts.InOutStatus.UNKNOWN
    assert panel.aux_out_status(2) == consts.InOutStatus.UNKNOWN


def test_core_get_device_param():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"), bytes.fromhex("d18a0000915255"),
            bytes.fromhex("aa01c80400"), bytes.fromhex("d18a000055")
        ]

        assert panel.connect() is True

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c84800"),
                                                     bytes.fromhex(
            "d18a02007e5a4b465056657273696f6e3d31302c4c6f636b436f756e743d322c5265616465"
            "72436f756e743d342c417578496e436f756e743d322c4175784f7574436f756e743d32783f55")]
        params = panel.get_device_param(["~ZKFPVersion:", "LockCount", "ReaderCount", "AuxInCount", "AuxOutCount"])
        assert params["~ZKFPVersion"] == "10"
        assert params["LockCount"] == "2"
        assert params["ReaderCount"] == "4"
        assert params["AuxInCount"] == "2"
        assert params["AuxOutCount"] == "2"


def test_core_connect_response_incomplete():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"), bytes.fromhex("d18a0000915255"),
            bytes.fromhex("aa01c80400"), bytes.fromhex("d18a000055")
        ]

        assert panel.connect() is True

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c80800"), bytes.fromhex("d18a020012345678")]
        with pytest.raises(ValueError):
            panel.get_device_param([])


def test_core_connect_response_no_data():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        panel.receive_retries = 1
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"), bytes.fromhex("d18a0000915255"),
            bytes(), bytes()
        ]

        assert panel.connect() is True

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c80800"), bytes()]
        with pytest.raises(ValueError):
            panel.get_device_param([])


def test_core_connect_session_less():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            # Reject response to session connect attempt
            bytes.fromhex("aa01c90100"), bytes.fromhex("f313d955"),
            # Confirm session-less connection attempt
            bytes.fromhex("aa00c80000"), bytes.fromhex("81fe55"),
            # Session-less response to init-getparams
            bytes.fromhex("aa00c84800"), bytes.fromhex("7e53657269616c4e756d6265723d4444473831333030313630393232303034"
                                                       "30312c4c6f636b436f756e743d342c417578496e436f756e743d342c417578"
                                                       "4f7574436f756e743d343b3f55"),
        ]

        assert panel.connect() is True
        assert panel.serial_number == "DDG8130016092200401"
        assert panel.nr_of_locks == 4
        assert panel.nr_aux_out == 4
        assert panel.nr_aux_in == 4


def test_core_connect_password():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 12
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"), bytes.fromhex("1420fefe4c5e55"),
            bytes.fromhex("aa01c80000"), bytes.fromhex("1420efe955")
        ]

        assert panel.connect("banana123") is True
        assert mock_socket.return_value.send.call_count == 2
        mock_socket.return_value.send.assert_any_call(bytes.fromhex("aa01760d00fefefefe62616E616E61313233961955"))


def test_core_lock_status():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c80400"),
                                                     bytes.fromhex("eb6600005c7f55"),
                                                     bytes.fromhex("aa01c84600"),
                                                     bytes.fromhex(
             "eb6601007e53657269616c4e756d6265723d363430343136323130313638392c4c6f636b"
             "436f756e743d322c417578496e436f756e743d322c4175784f7574436f756e743d326a2255")]

        assert panel.connect() is True
        assert panel.nr_of_locks == 2
        assert panel.lock_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.lock_status(2) == consts.InOutStatus.UNKNOWN
        assert panel.lock_status(3) == consts.InOutStatus.UNKNOWN
        assert panel.lock_status(4) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c81400"),
                                                     bytes.fromhex("eb66030003000000110000000001ff00f5c1ca2caa1f55")]
        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], rtlog.DoorAlarmStatusRecord)
        assert logs[0].door_sensor_status(1) == consts.InOutStatus.CLOSED
        assert logs[0].door_sensor_status(2) == consts.InOutStatus.UNKNOWN
        assert panel.lock_status(1) == consts.InOutStatus.CLOSED
        assert panel.lock_status(2) == consts.InOutStatus.UNKNOWN
        assert panel.lock_status(3) == consts.InOutStatus.UNKNOWN
        assert panel.lock_status(4) == consts.InOutStatus.UNKNOWN


def test_core_aux_in_status():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c80400"),
                                                     bytes.fromhex("eb6600005c7f55"),
                                                     bytes.fromhex("aa01c84600"),
                                                     bytes.fromhex(
             "eb6601007e53657269616c4e756d6265723d363430343136323130313638392c4c6f636b"
             "436f756e743d322c417578496e436f756e743d322c4175784f7574436f756e743d326a2255")]

        assert panel.connect() is True
        assert panel.nr_aux_in == 2
        assert panel.aux_in_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_in_status(2) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c81400"),
                                                     bytes.fromhex("eb663c000000000000000000c802dd02f5c3ca2c0abe55")]
        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], rtlog.EventRecord)
        assert logs[0].port_nr == 2
        assert logs[0].event_type == consts.EventType.AUX_INPUT_SHORT
        assert panel.aux_in_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_in_status(2) == consts.InOutStatus.CLOSED

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c81400"),
                                                     bytes.fromhex("eb663e000000000000000000c802dc02f9c3ca2ca98755")]
        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], rtlog.EventRecord)
        assert logs[0].port_nr == 2
        assert logs[0].event_type == consts.EventType.AUX_INPUT_DISCONNECT
        assert panel.aux_in_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_in_status(2) == consts.InOutStatus.OPEN


def test_core_aux_out_status():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c80400"),
                                                     bytes.fromhex("eb6600005c7f55"),
                                                     bytes.fromhex("aa01c84600"),
                                                     bytes.fromhex(
             "eb6601007e53657269616c4e756d6265723d363430343136323130313638392c4c6f636b"
             "436f756e743d322c417578496e436f756e743d322c4175784f7574436f756e743d326a2255")]

        assert panel.connect() is True
        assert panel.nr_aux_out == 2
        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c81400"),
                                                     bytes.fromhex("eb6643000000000000000000c8020c0229c4ca2cbb6255")]
        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], rtlog.EventRecord)
        assert logs[0].port_nr == 2
        assert logs[0].event_type == consts.EventType.OPEN_AUX_OUTPUT
        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.OPEN

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c81400"),
                                                     bytes.fromhex("eb664c000000000000000000c8020d0271c4ca2c9ac455")]
        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], rtlog.EventRecord)
        assert logs[0].port_nr == 2
        assert logs[0].event_type == consts.EventType.CLOSE_AUX_OUTPUT
        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.CLOSED


def test_core_aux_out_open_close():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c80400"),
                                                     bytes.fromhex("eb6600005c7f55"),
                                                     bytes.fromhex("aa01c84600"),
                                                     bytes.fromhex(
             "eb6601007e53657269616c4e756d6265723d363430343136323130313638392c4c6f636b"
             "436f756e743d322c417578496e436f756e743d322c4175784f7574436f756e743d326a2255")]

        assert panel.connect() is True
        assert panel.nr_aux_out == 2
        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c80400"),
                                                     bytes.fromhex("eb6602005d1f55")]

        command = controldevice.ControlDeviceOutput(2, consts.ControlOutputAddress.AUX_OUTPUT, 2)
        panel.control_device(command)

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c81400"),
                                                     bytes.fromhex("eb6643000000000000000000c8020c0229c4ca2cbb6255")]
        panel.get_rt_log()
        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.OPEN

        time.sleep(2.1)

        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.CLOSED


def test_core_door_settings():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c80400"),
                                                     bytes.fromhex("4d9cfefe9f2655"),
                                                     bytes.fromhex("aa01c82a00"),
                                                     bytes.fromhex("4d9cfffe4c6f636b436f756e743d322c417578496e436f75"
                                                                   "6e743d322c4175784f7574436f756e743d32bb5755")]

        assert panel.connect() is True
        assert panel.nr_of_locks == 2

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa00c83d00"),
                                                     bytes.fromhex("4d9c08ff446f6f723153656e736f72547970653d322c446f"
                                                                   "6f723144726976657274696d653d312c446f6f7231446574"
                                                                   "6563746f7274696d653d323530b18d55"),
                                                     bytes.fromhex("aa00c83c00"),
                                                     bytes.fromhex("4d9c09ff446f6f723253656e736f72547970653d302c446f"
                                                                   "6f723244726976657274696d653d352c446f6f7232446574"
                                                                   "6563746f7274696d653d3135158355")]

        assert panel.door_settings(1).sensor_type == consts.DoorSensorType.NORMAL_CLOSE
        assert panel.door_settings(1).lock_drive_time == 1
        assert panel.door_settings(1).door_alarm_timeout == 250
        assert panel.door_settings(2).sensor_type == consts.DoorSensorType.NONE
        assert panel.door_settings(2).lock_drive_time == 5
        assert panel.door_settings(2).door_alarm_timeout == 15


def test_core_update_inout_status_exit_button():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c80400"),
                                                     bytes.fromhex("4d9cfefe9f2655"),
                                                     bytes.fromhex("aa01c82a00"),
                                                     bytes.fromhex("4d9cfffe4c6f636b436f756e743d322c417578496e436f75"
                                                                   "6e743d322c4175784f7574436f756e743d32bb5755")]

        assert panel.connect() is True
        assert panel.nr_of_locks == 2
        assert panel.lock_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.lock_status(2) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa00c81400"),
                                                     bytes.fromhex("4d9c06ff03000000111000000001ff0013ecfd2d4ae555")]

        panel.get_rt_log()
        assert panel.lock_status(1) == consts.InOutStatus.CLOSED
        assert panel.lock_status(2) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa00c81400"),
                                                     bytes.fromhex("4d9c07ff0000000000000000c802ca0215ecfd2d710f55"),
                                                     bytes.fromhex("aa00c83d00"),
                                                     bytes.fromhex("4d9c08ff446f6f723153656e736f72547970653d322c446f"
                                                                   "6f723144726976657274696d653d312c446f6f7231446574"
                                                                   "6563746f7274696d653d323530b18d55"),
                                                     bytes.fromhex("aa00c83c00"),
                                                     bytes.fromhex("4d9c09ff446f6f723253656e736f72547970653d302c446f"
                                                                   "6f723244726976657274696d653d312c446f6f7232446574"
                                                                   "6563746f7274696d653d3135507055")]

        panel.get_rt_log()
        assert panel.lock_status(1) == consts.InOutStatus.CLOSED
        assert panel.lock_status(2) == consts.InOutStatus.OPEN
        assert panel.door_settings(2).sensor_type == consts.DoorSensorType.NONE
        assert panel.door_settings(2).lock_drive_time == 1

        time.sleep(panel.door_settings(2).lock_drive_time + 0.1)

        assert panel.lock_status(2) == consts.InOutStatus.CLOSED

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa00c81400"),
                                                     bytes.fromhex("4d9c06ff03000000111000000001ff0013ecfd2d4ae555")]

        # Subsequent DoorAlarmStatus logs with door 2 status 'unknown' are ignored,
        # last-known status better than unknown is used
        panel.get_rt_log()
        assert panel.lock_status(1) == consts.InOutStatus.CLOSED
        assert panel.lock_status(2) == consts.InOutStatus.CLOSED

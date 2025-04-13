import time
from datetime import datetime
from unittest import mock

import pytest

from c3 import consts, controldevice, rtlog
from c3.core import C3


@pytest.fixture
def data_cfg_response_data() -> str:
    return (
        "4ac70200757365723d312c5549443d69312c436172644e6f3d69322c50696e3d69332c50617373776f72643d73342c47"
        "726f75703d69352c537461727454696d653d69362c456e6454696d653d69372c4e616d653d73382c5375706572417574"
        "686f72697a653d69390a75736572617574686f72697a653d322c50696e3d69312c417574686f72697a6554696d657a6f"
        "6e6549643d69322c417574686f72697a65446f6f7249643d69330a686f6c696461793d332c486f6c696461793d69312c"
        "486f6c69646179547970653d69322c4c6f6f703d69330a74696d657a6f6e653d342c54696d657a6f6e6549643d69312c"
        "53756e54696d65313d69322c53756e54696d65323d69332c53756e54696d65333d69342c4d6f6e54696d65313d69352c"
        "4d6f6e54696d65323d69362c4d6f6e54696d65333d69372c54756554696d65313d69382c54756554696d65323d69392c"
        "54756554696d65333d6931302c57656454696d65313d6931312c57656454696d65323d6931322c57656454696d65333d"
        "6931332c54687554696d65313d6931342c54687554696d65323d6931352c54687554696d65333d6931362c4672695469"
        "6d65313d6931372c46726954696d65323d6931382c46726954696d65333d6931392c53617454696d65313d6932302c53"
        "617454696d65323d6932312c53617454696d65333d6932322c486f6c3154696d65313d6932332c486f6c3154696d6532"
        "3d6932342c486f6c3154696d65333d6932352c486f6c3254696d65313d6932362c486f6c3254696d65323d6932372c48"
        "6f6c3254696d65333d6932382c486f6c3354696d65313d6932392c486f6c3354696d65323d6933302c486f6c3354696d"
        "65333d6933310a7472616e73616374696f6e3d352c436172646e6f3d69312c50696e3d69322c56657269666965643d69"
        "332c446f6f7249443d69342c4576656e74547970653d69352c496e4f757453746174653d69362c54696d655f7365636f"
        "6e643d69370a6669727374636172643d362c50696e3d69312c446f6f7249443d69322c54696d657a6f6e6549443d6933"
        "0a6d756c74696d636172643d372c496e6465783d69312c446f6f7249643d69322c47726f7570313d69332c47726f7570"
        "323d69342c47726f7570333d69352c47726f7570343d69362c47726f7570353d69370a696e6f757466756e3d382c496e"
        "6465783d69312c4576656e74547970653d69322c496e416464723d69332c4f7574547970653d69342c4f757441646472"
        "3d69352c4f757454696d653d69362c52657365727665643d69370a74656d706c6174653d392c53697a653d69312c5069"
        "6e3d69322c46696e67657249443d69332c56616c69643d69342c54656d706c6174653d73350a74656d706c6174657631"
        "303d31302c53697a653d69312c5549443d69322c50696e3d69332c46696e67657249443d69342c56616c69643d69352c"
        "54656d706c6174653d42362c526573766572643d69372c456e645461673d69380a6c6f7373636172643d31312c436172"
        "644e6f3d69312c52657365727665643d69320a75736572747970653d31322c50696e3d69312c547970653d69320a7769"
        "6567616e64666d743d31332c50696e3d69312c4e616d653d73322c5767436f756e743d69332c466f726d61743d73340a70c055"
    )


def test_core_init():
    panel = C3("localhost")
    assert panel.nr_of_locks == 0
    assert panel.nr_aux_in == 0
    assert panel.nr_aux_out == 0
    assert panel.lock_status(1) == consts.InOutStatus.UNKNOWN
    assert panel.aux_in_status(1) == consts.InOutStatus.UNKNOWN
    assert panel.aux_out_status(2) == consts.InOutStatus.UNKNOWN


def test_core_set_device_datetime():
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("d18a0000915255"),
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("d18a000055"),
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("d18a0003d15355"),
        ]

        assert panel.connect() is True
        test_time = datetime(2025, 4, 13, hour=15, minute=54, second=12)
        panel.set_device_datetime(test_time)

        assert mock_socket.return_value.send.call_count == 3
        mock_socket.return_value.send.assert_any_call(
            bytearray(b"\xaa\x01\x03\x16\x00\xd1\x8a\x00\xffDateTime=812649252\x05>U")
        )


def test_core_get_device_param():
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("d18a0000915255"),
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("d18a000055"),
        ]

        assert panel.connect() is True

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c84800"),
            bytes.fromhex(
                "d18a02007e5a4b465056657273696f6e3d31302c4c6f636b436f756e743d322c5265616465"
                "72436f756e743d342c417578496e436f756e743d322c4175784f7574436f756e743d32783f55"
            ),
        ]
        params = panel.get_device_param(
            ["~ZKFPVersion:", "LockCount", "ReaderCount", "AuxInCount", "AuxOutCount"]
        )
        assert params["~ZKFPVersion"] == "10"
        assert params["LockCount"] == "2"
        assert params["ReaderCount"] == "4"
        assert params["AuxInCount"] == "2"
        assert params["AuxOutCount"] == "2"


def test_core_get_device_data_cfg(data_cfg_response_data):
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa00c80400"),
            bytes.fromhex("4ac70100ee3d55"),
            bytes.fromhex("aa01c80200"),
            bytes.fromhex("4ac797c355"),
        ]

        assert panel.connect() is True
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa00c8b004"),
            bytes.fromhex(data_cfg_response_data),
        ]

        data_cfg = panel._get_device_data_cfg()
        assert len(data_cfg) == 13
        user_cfg = data_cfg[0]
        assert user_cfg.name == "user"
        assert user_cfg.index == 1
        assert len(user_cfg.fields) == 9
        assert user_cfg.fields[5].name == "StartTime"
        assert user_cfg.fields[5].type == "i"
        assert user_cfg.fields[5].index == 6
        assert user_cfg.fields[7].name == "Name"
        assert user_cfg.fields[7].type == "s"
        assert user_cfg.fields[7].index == 8


def test_core_get_device_data_user(data_cfg_response_data):
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa00c80400"),
            bytes.fromhex("4ac70100ee3d55"),
            bytes.fromhex("aa01c80200"),
            bytes.fromhex("4ac797c355"),
        ]

        assert panel.connect() is True
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa00c8b004"),
            bytes.fromhex(data_cfg_response_data),
            bytes.fromhex("aa00c83d00"),
            bytes.fromhex(
                "4ac70400"
                "0109010203040506070809"
                "01010387D6120376543200010001000100000100"
                "010203a1a3a303b1b2b3000100042a893401049fb03401000100"
                "b44b55"
            ),
        ]

        user_data = panel.get_device_data(table_name="user")
        assert len(user_data) == 2
        assert user_data[0]["UID"] == 1
        assert user_data[0]["CardNo"] == 1234567
        assert user_data[1]["StartTime"] == 20220202
        assert user_data[1]["EndTime"] == 20230303


def test_core_connect_response_incomplete():
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("d18a0000915255"),
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("d18a000055"),
        ]

        assert panel.connect() is True

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80800"),
            bytes.fromhex("d18a020012345678"),
        ]
        with pytest.raises(ValueError):
            panel.get_device_param([])


def test_core_connect_response_no_data():
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        panel.receive_retries = 1
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("d18a0000915255"),
            bytes(),
            bytes(),
        ]

        assert panel.connect() is True

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80800"),
            bytes(),
        ]
        with pytest.raises(ValueError):
            panel.get_device_param([])


def test_core_connect_session_less():
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            # Reject response to session connect attempt
            bytes.fromhex("aa01c90100"),
            bytes.fromhex("f313d955"),
            # Confirm session-less connection attempt
            bytes.fromhex("aa00c80000"),
            bytes.fromhex("81fe55"),
            # Session-less response to init-getparams
            bytes.fromhex("aa00c84800"),
            bytes.fromhex(
                "7e53657269616c4e756d6265723d4444473831333030313630393232303034"
                "30312c4c6f636b436f756e743d342c417578496e436f756e743d342c417578"
                "4f7574436f756e743d343b3f55"
            ),
        ]

        assert panel.connect() is True
        assert panel.serial_number == "DDG8130016092200401"
        assert panel.nr_of_locks == 4
        assert panel.nr_aux_out == 4
        assert panel.nr_aux_in == 4


def test_core_connect_password():
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 12
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("1420fefe4c5e55"),
            bytes.fromhex("aa01c80000"),
            bytes.fromhex("1420efe955"),
        ]

        assert panel.connect("banana123") is True
        assert mock_socket.return_value.send.call_count == 2
        mock_socket.return_value.send.assert_any_call(
            bytes.fromhex("aa01760d00fefefefe62616E616E61313233961955")
        )


def test_core_lock_status():
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("eb6600005c7f55"),
            bytes.fromhex("aa01c84600"),
            bytes.fromhex(
                "eb6601007e53657269616c4e756d6265723d363430343136323130313638392c4c6f636b"
                "436f756e743d322c417578496e436f756e743d322c4175784f7574436f756e743d326a2255"
            ),
        ]

        assert panel.connect() is True
        assert panel.nr_of_locks == 2
        assert panel.lock_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.lock_status(2) == consts.InOutStatus.UNKNOWN
        assert panel.lock_status(3) == consts.InOutStatus.UNKNOWN
        assert panel.lock_status(4) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c81400"),
            bytes.fromhex("eb66030003000000110000000001ff00f5c1ca2caa1f55"),
        ]
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
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("eb6600005c7f55"),
            bytes.fromhex("aa01c84600"),
            bytes.fromhex(
                "eb6601007e53657269616c4e756d6265723d363430343136323130313638392c4c6f636b"
                "436f756e743d322c417578496e436f756e743d322c4175784f7574436f756e743d326a2255"
            ),
        ]

        assert panel.connect() is True
        assert panel.nr_aux_in == 2
        assert panel.aux_in_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_in_status(2) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c81400"),
            bytes.fromhex("eb663c000000000000000000c802dd02f5c3ca2c0abe55"),
        ]
        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], rtlog.EventRecord)
        assert logs[0].port_nr == 2
        assert logs[0].event_type == consts.EventType.AUX_INPUT_SHORT
        assert panel.aux_in_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_in_status(2) == consts.InOutStatus.CLOSED

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c81400"),
            bytes.fromhex("eb663e000000000000000000c802dc02f9c3ca2ca98755"),
        ]
        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], rtlog.EventRecord)
        assert logs[0].port_nr == 2
        assert logs[0].event_type == consts.EventType.AUX_INPUT_DISCONNECT
        assert panel.aux_in_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_in_status(2) == consts.InOutStatus.OPEN


def test_core_aux_out_status():
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("eb6600005c7f55"),
            bytes.fromhex("aa01c84600"),
            bytes.fromhex(
                "eb6601007e53657269616c4e756d6265723d363430343136323130313638392c4c6f636b"
                "436f756e743d322c417578496e436f756e743d322c4175784f7574436f756e743d326a2255"
            ),
        ]

        assert panel.connect() is True
        assert panel.nr_aux_out == 2
        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c81400"),
            bytes.fromhex("eb6643000000000000000000c8020c0229c4ca2cbb6255"),
        ]
        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], rtlog.EventRecord)
        assert logs[0].port_nr == 2
        assert logs[0].event_type == consts.EventType.OPEN_AUX_OUTPUT
        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.OPEN

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c81400"),
            bytes.fromhex("eb664c000000000000000000c8020d0271c4ca2c9ac455"),
        ]
        logs = panel.get_rt_log()
        assert len(logs) == 1
        assert isinstance(logs[0], rtlog.EventRecord)
        assert logs[0].port_nr == 2
        assert logs[0].event_type == consts.EventType.CLOSE_AUX_OUTPUT
        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.CLOSED


def test_core_aux_out_open_close():
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("eb6600005c7f55"),
            bytes.fromhex("aa01c84600"),
            bytes.fromhex(
                "eb6601007e53657269616c4e756d6265723d363430343136323130313638392c4c6f636b"
                "436f756e743d322c417578496e436f756e743d322c4175784f7574436f756e743d326a2255"
            ),
        ]

        assert panel.connect() is True
        assert panel.nr_aux_out == 2
        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("eb6602005d1f55"),
        ]

        command = controldevice.ControlDeviceOutput(
            2, consts.ControlOutputAddress.AUX_OUTPUT, 2
        )
        panel.control_device(command)

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c81400"),
            bytes.fromhex("eb6643000000000000000000c8020c0229c4ca2cbb6255"),
        ]
        panel.get_rt_log()
        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.OPEN

        time.sleep(2.1)

        assert panel.aux_out_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.aux_out_status(2) == consts.InOutStatus.CLOSED


def test_core_door_settings():
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("4d9cfefe9f2655"),
            bytes.fromhex("aa01c82a00"),
            bytes.fromhex(
                "4d9cfffe4c6f636b436f756e743d322c417578496e436f75"
                "6e743d322c4175784f7574436f756e743d32bb5755"
            ),
        ]

        assert panel.connect() is True
        assert panel.nr_of_locks == 2

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa00c83d00"),
            bytes.fromhex(
                "4d9c08ff446f6f723153656e736f72547970653d322c446f"
                "6f723144726976657274696d653d312c446f6f7231446574"
                "6563746f7274696d653d323530b18d55"
            ),
            bytes.fromhex("aa00c83c00"),
            bytes.fromhex(
                "4d9c09ff446f6f723253656e736f72547970653d302c446f"
                "6f723244726976657274696d653d352c446f6f7232446574"
                "6563746f7274696d653d3135158355"
            ),
        ]

        assert panel.door_settings(1).sensor_type == consts.DoorSensorType.NORMAL_CLOSE
        assert panel.door_settings(1).lock_drive_time == 1
        assert panel.door_settings(1).door_alarm_timeout == 250
        assert panel.door_settings(2).sensor_type == consts.DoorSensorType.NONE
        assert panel.door_settings(2).lock_drive_time == 5
        assert panel.door_settings(2).door_alarm_timeout == 15


def test_core_update_inout_status_exit_button():
    with mock.patch("socket.socket") as mock_socket:
        panel = C3("localhost")
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa01c80400"),
            bytes.fromhex("4d9cfefe9f2655"),
            bytes.fromhex("aa01c82a00"),
            bytes.fromhex(
                "4d9cfffe4c6f636b436f756e743d322c417578496e436f75"
                "6e743d322c4175784f7574436f756e743d32bb5755"
            ),
        ]

        assert panel.connect() is True
        assert panel.nr_of_locks == 2
        assert panel.lock_status(1) == consts.InOutStatus.UNKNOWN
        assert panel.lock_status(2) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa00c81400"),
            bytes.fromhex("4d9c06ff03000000111000000001ff0013ecfd2d4ae555"),
        ]

        panel.get_rt_log()
        assert panel.lock_status(1) == consts.InOutStatus.CLOSED
        assert panel.lock_status(2) == consts.InOutStatus.UNKNOWN

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa00c81400"),
            bytes.fromhex("4d9c07ff0000000000000000c802ca0215ecfd2d710f55"),
            bytes.fromhex("aa00c83d00"),
            bytes.fromhex(
                "4d9c08ff446f6f723153656e736f72547970653d322c446f"
                "6f723144726976657274696d653d312c446f6f7231446574"
                "6563746f7274696d653d323530b18d55"
            ),
            bytes.fromhex("aa00c83c00"),
            bytes.fromhex(
                "4d9c09ff446f6f723253656e736f72547970653d302c446f"
                "6f723244726976657274696d653d312c446f6f7232446574"
                "6563746f7274696d653d3135507055"
            ),
        ]

        panel.get_rt_log()
        assert panel.lock_status(1) == consts.InOutStatus.CLOSED
        assert panel.lock_status(2) == consts.InOutStatus.OPEN
        assert panel.door_settings(2).sensor_type == consts.DoorSensorType.NONE
        assert panel.door_settings(2).lock_drive_time == 1

        time.sleep(panel.door_settings(2).lock_drive_time + 0.1)

        assert panel.lock_status(2) == consts.InOutStatus.CLOSED

        mock_socket.return_value.recv.side_effect = [
            bytes.fromhex("aa00c81400"),
            bytes.fromhex("4d9c06ff03000000111000000001ff0013ecfd2d4ae555"),
        ]

        # Subsequent DoorAlarmStatus logs with door 2 status 'unknown' are ignored,
        # last-known status better than unknown is used
        panel.get_rt_log()
        assert panel.lock_status(1) == consts.InOutStatus.CLOSED
        assert panel.lock_status(2) == consts.InOutStatus.CLOSED

from unittest import mock

from c3 import rtlog
from c3.core import C3
from c3 import consts


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
        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c80400"),
                                                     bytes.fromhex("d18a0000915255")]

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

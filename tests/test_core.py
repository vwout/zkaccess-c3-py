from unittest import mock
from c3.core import C3


def test_core_get_device_param():
    with mock.patch('socket.socket') as mock_socket:
        panel = C3('localhost')
        mock_socket.return_value.send.return_value = 8
        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c80400"), bytes.fromhex("d18a0000915255")]

        assert panel.connect() is True

        mock_socket.return_value.recv.side_effect = [bytes.fromhex("aa01c84800"), bytes.fromhex(
            "d18a02007e5a4b465056657273696f6e3d31302c4c6f636b436f756e743d322c5265616465"
            "72436f756e743d342c417578496e436f756e743d322c4175784f7574436f756e743d32783f55")]
        params = panel.get_device_param(["~ZKFPVersion:", "LockCount", "ReaderCount", "AuxInCount", "AuxOutCount"])
        assert params["~ZKFPVersion"] == "10"
        assert params["LockCount"] == "2"
        assert params["ReaderCount"] == "4"
        assert params["AuxInCount"] == "2"
        assert params["AuxOutCount"] == "2"

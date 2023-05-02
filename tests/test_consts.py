from c3.consts import *


def test_commands():
    connect_cmd = Command.CONNECT
    assert 0x76 == connect_cmd
    connect_reply = C3_REPLY_OK
    assert 0xC8 == connect_reply


def test_control_operation():
    cancel_alarm = ControlOperation.CANCEL_ALARM
    assert 2 == int(cancel_alarm)
    assert "2" == str(cancel_alarm)
    assert "Cancel alarm" == cancel_alarm.description
    assert "2" == "%s" % cancel_alarm
    assert "Cancel alarm" == "%r" % cancel_alarm

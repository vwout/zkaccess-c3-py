from c3.consts import *


def test_commands():
    connect = C3_COMMAND_CONNECT
    assert 0x76 == connect.request
    assert 0xC8 == connect.reply


def test_control_operation():
    cancel_alarm = ControlOperation.CANCEL_ALARM
    assert 2 == int(cancel_alarm)
    assert "2" == str(cancel_alarm)
    assert "Cancel alarm" == cancel_alarm.description
    assert "2" == "%s" % cancel_alarm
    assert "Cancel alarm" == "%r" % cancel_alarm

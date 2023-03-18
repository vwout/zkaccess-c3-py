from c3 import controldevice
from c3 import consts


def test_c3_device_control_message_output_door():
    output_operation = controldevice.ControlDeviceOutput(1, consts.ControlOutputAddress.DOOR_OUTPUT, 200)
    assert bytes([0x01, 0x01, 0x01, 0xc8, 0x00]) == output_operation.to_bytes()
    print(repr(output_operation))


def test_c3_device_control_message_output_door_int():
    output_operation = controldevice.ControlDeviceOutput(3, 1, 200)
    assert bytes([0x01, 0x03, 0x01, 0xc8, 0x00]) == output_operation.to_bytes()
    print(repr(output_operation))


def test_c3_device_control_message_output_aux():
    output_operation = controldevice.ControlDeviceOutput(2, consts.ControlOutputAddress.AUX_OUTPUT, 100)
    assert bytes([0x01, 0x02, 0x02, 0x64, 0x00]) == output_operation.to_bytes()
    print(repr(output_operation))


def test_c3_device_control_message_cancel():
    output_operation = controldevice.ControlDeviceCancelAlarms()
    assert bytes([0x02, 0x00, 0x00, 0x00, 0x00]) == output_operation.to_bytes()
    print(repr(output_operation))


def test_c3_device_control_message_restart():
    output_operation = controldevice.ControlDeviceRestart()
    assert bytes([0x03, 0x00, 0x00, 0x00, 0x00]) == output_operation.to_bytes()
    print(repr(output_operation))


def test_c3_device_control_message_nostate():
    output_operation = controldevice.ControlDeviceNormalOpenStateEnable(2, 1)
    assert bytes([0x04, 0x02, 0x01, 0x00, 0x00]) == output_operation.to_bytes()

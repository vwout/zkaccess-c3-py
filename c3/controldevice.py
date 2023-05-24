from abc import ABC

from c3 import consts


class ControlDeviceBase(ABC):
    """A ControlDevice is a binary message of 5 bytes send to the C3 access panel.
    It changes the states of the doors, auxiliary relays and alarms.
    All multibyte values are stored as Little-endian.

    Byte       0  1  2  3  4
               01:01:01:c8:00
    Operation: |
               01 => 1 (1: output, 2: cancel alarm, 3: restart device_name, 4: enable/disable normal open state)
    Param 1:      |
    Param 2:         |
    Param 3:            |
    Param 4:               |

    The meaning of the parameters is depending on the Operation code.
    Param 4 is reserved for future use (defaults to 0)
    Operation 1: Output operation
      Param 1: Door number or auxiliary output number
      Param 2: The address type of output operation (1: Door output, 2: Auxiliary output)
      Param 3: Duration of the open operation, only for address type = 1 (door output).
               0: close, 255: normal open state, 1~254: normal open duration
    Operation 2: Cancel alarm
      Param 1: 0 (null)
      Param 2: 0 (null)
      Param 3: 0 (null)
    Operation 3: Restart device_name
      Param 1: 0 (null)
      Param 2: 0 (null)
      Param 3: 0 (null)
    Operation 3: Enable/disable normal open state
      Param 1: Door number
      Param 2: Enable / disable (0: disable, 1: enable'
      Param 3: 0 (null)
    """

    def __init__(self, operation: consts.ControlOperation, *args: int):
        """Constructor to initialize base class.
        The param1, param2, param3 and param4 values are provided as variable argument."""
        self.operation: consts.ControlOperation = operation
        self.param1: int = args[0] if len(args) > 0 else None
        self.param2: int = args[1] if len(args) > 1 else None
        self.param3: int = args[2] if len(args) > 2 else None
        self.param4: int = args[3] if len(args) > 3 else None

    @classmethod
    def from_bytes(cls, data: bytes):
        return ControlDeviceBase(*data)

    def to_bytes(self) -> bytes:
        return bytes([self.operation, self.param1 or 0, self.param2 or 0, self.param3 or 0, self.param4 or 0])

    def __repr__(self):
        return "\r\n".join([
            "%-12s %-10s (%s)" % ("operation", self.operation, repr(self.operation)),
            "%-12s %-10s" % ("param1", self.param1),
            "%-12s %-10s" % ("param2", self.param2),
            "%-12s %-10s" % ("param3", self.param3),
            "%-12s %-10s" % ("param4", self.param4),
        ])


class ControlDeviceOutput(ControlDeviceBase):
    def __init__(self, output_number: int, address: consts.ControlOutputAddress, duration: int):
        ControlDeviceBase.__init__(self, consts.ControlOperation.OUTPUT, output_number, address, duration)

    @property
    def output_number(self) -> int:
        return self.param1

    @property
    def address(self) -> int:
        return self.param2

    @property
    def duration(self) -> int:
        return self.param3

    def __repr__(self):
        return "\r\n".join([
            "ControlDevice Output Operation:"
            "%-12s %-10s (%s)" % ("operation", self.operation, repr(self.operation)),
            "%-12s %-10s (Door/Aux Number)" % ("param1", self.output_number),
            "%-12s %-10s %s" % ("param2", self.param2, repr(consts.ControlOutputAddress(self.address))),
            "%-12s %-10s (Duration)" % ("param3", self.duration),
        ])


class ControlDeviceCancelAlarms(ControlDeviceBase):
    def __init__(self):
        ControlDeviceBase.__init__(self, consts.ControlOperation.CANCEL_ALARM)

    def __repr__(self):
        return "\r\n".join([
            "ControlDevice Cancel Alarm Operation:",
            ControlDeviceBase.__repr__(self)
        ])


class ControlDeviceNormalOpenStateEnable(ControlDeviceBase):
    def __init__(self, door_number: int, enable: bool):
        ControlDeviceBase.__init__(self, consts.ControlOperation.ENDIS_NO_STATE, door_number, enable)

    @property
    def door_number(self) -> int:
        return self.param1

    @property
    def enabled(self) -> bool:
        return bool(self.param2)

    def __repr__(self):
        return "\r\n".join([
            "ControlDevice Normal Open State Operation:"
            "%-12s %-10s (%s)" % ("operation", self.operation, repr(self.operation)),
            "%-12s %-10s (Door Number)" % ("param1", self.door_number),
            "%-12s %-10s %s" % ("param2", self.param2, "Enable" if self.enabled else "Disable"),
        ])


class ControlDeviceRestart(ControlDeviceBase):
    def __init__(self):
        ControlDeviceBase.__init__(self, consts.ControlOperation.RESTART_DEVICE)

    def __repr__(self):
        return "\r\n".join([
            "ControlDevice Restart Operation:",
            ControlDeviceBase.__repr__(self)
        ])

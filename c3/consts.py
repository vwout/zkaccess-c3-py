from enum import Enum, IntEnum, unique
from collections import namedtuple

# Defaults
C3_PORT_DEFAULT = 4370

# Protocol commands
C3_MESSAGE_START        = 0xAA
C3_MESSAGE_END          = 0x55
C3_PROTOCOL_VERSION     = 0x01

CommandStruct = namedtuple("Command" , "request reply")
C3_COMMAND_CONNECT      = CommandStruct(0x76, 0xC8)
C3_COMMAND_DISCONNECT   = CommandStruct(0x02, 0xC8)
C3_COMMAND_GETPARAM     = CommandStruct(0x04, 0xC8)
C3_COMMAND_DATATABLECFG = CommandStruct(0x06, 0xC8)
C3_COMMAND_CONTROL      = CommandStruct(0x05, 0xC8)
C3_COMMAND_RTLOG        = CommandStruct(0x0B, 0xC8)

@unique
class IntEnumWithDescription(IntEnum):
    def __new__(cls, *args, **kwds):
        obj = int.__new__(cls, args[0])
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, description: str = None):
        self._description_ = description

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return self._description_

    # this makes sure that the description is read-only
    @property
    def description(self):
        return self._description_


# Control operations
class ControlOperation(IntEnumWithDescription):
    OUTPUT         = 1, "Output operation (door or auxilary)"
    CANCEL_ALARM   = 2, "Cancel alarm"
    RESTART_DEVICE = 3, "Restart Device"
    ENDIS_NO_STATE = 4, "Enable/disable normal open state"

class ControlOutputAddress(IntEnumWithDescription):
    DOOR_OUTPUT = 1, "Door output"
    AUX_OUTPUT  = 2, "Auxiliary output"

# Event values
class VerificationMode(IntEnumWithDescription):
    NONE               = 0, "None"
    FINGER             = 1, "Only finger"
    PASSWORD           = 3, "Only password"
    CARD               = 4, "Only card"
    CARD_WITH_PASSWORD = 11, "Card and password"
    OTHER              = 200, "Others"

class EventType(IntEnumWithDescription):
    # [0]   = "Normal Punch Open",
    # [1]   = "Punch during Normal Open Time Zone",
    # [2]   = "First Card Normal Open (Punch Card)",
    # [3]   = "Multi-Card Open (Punching Card)",
    # [4]   = "Emergency Password Open",
    # [5]   = "Open during Normal Open Time Zone",
    # [6]   = "Linkage Event Triggered",
    # [7]   = "Cancel Alarm",
    # [8]   = "Remote Opening",
    # [9]   = "Remote Closing",
    # [10]  = "Disable Intraday Normal Open Time Zone",
    # [11]  = "Enable Intraday Normal Open Time Zone",
    # [12]  = "Open Auxiliary Output",
    # [13]  = "Close Auxiliary Output",
    # [14]  = "Press Fingerprint Open",
    # [15]  = "Multi-Card Open (Press Fingerprint)",
    # [16]  = "Press Fingerprint during Normal Open Time Zone",
    # [17]  = "Card plus Fingerprint Open",
    # [18]  = "First Card Normal Open (Press Fingerprint)",
    # [19]  = "First Card Normal Open (Card plus Fingerprint)",
    # [20]  = "Too Short Punch Interval",
    # [21]  = "Door Inactive Time Zone (Punch Card)",
    # [22]  = "Illegal Time Zone",
    # [23]  = "Access Denied",
    # [24]  = "Anti-Passback",
    # [25]  = "Interlock",
    # [26]  = "Multi-Card Authentication (Punching Card)",
    # [27]  = "Unregistered Card",
    # [28]  = "Opening Timeout:",
    # [29]  = "Card Expired",
    # [30]  = "Password Error",
    # [31]  = "Too Short Fingerprint Pressing Interval",
    # [32]  = "Multi-Card Authentication (Press Fingerprint)",
    # [33]  = "Fingerprint Expired",
    # [34]  = "Unregistered Fingerprint",
    # [35]  = "Door Inactive Time Zone (Press Fingerprint)",
    # [36]  = "Door Inactive Time Zone (Exit Button)",
    # [37]  = "Failed to Close during Normal Open Time Zone",
    # [101] = "Duress Password Open",
    # [102] = "Opened Accidentally",
    # [103] = "Duress Fingerprint Open",
    # [200] = "Door Opened Correctly",
    # [201] = "Door Closed Correctly",
    # [202] = "Exit button Open",
    # [203] = "Multi-Card Open (Card plus Fingerprint)",
    # [204] = "Normal Open Time Zone Over",
    # [205] = "Remote Normal Opening",
    # [206] = "Device Start",
    # [220] = "Auxiliary Input Disconnected",
    # [221] = "Auxiliary Input Shorted",
    DOOR_ALARM_STATUS = 255, "Current door and alarm status"

class InOutStatus(IntEnumWithDescription):
    ENTRY = 0, "Entry"
    EXIT  = 3, "Exit"
    NONE  = 2, "None"

class AlarmStatus(IntEnumWithDescription):
    NONE              = 0, "None"
    ALARM             = 1, "Alarm"
    DOOR_OPEN_TIMEOUT = 2, "Door opening timeout"

class DssStatus(IntEnumWithDescription):
    UNKNOWN = 0, "No Door Status Sensor"
    CLOSED  = 1, "Door closed"
    OPEN    = 2, "Door open"



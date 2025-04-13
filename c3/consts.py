from enum import IntEnum, unique

# from collections import namedtuple

# Defaults
C3_PORT_DEFAULT = 4370
C3_PORT_BROADCAST = 65535

# Protocol commands
C3_MESSAGE_START = 0xAA
C3_MESSAGE_END = 0x55
C3_PROTOCOL_VERSION = 0x01
C3_DISCOVERY_MESSAGE = "CallSecurityDevice"


class Command(IntEnum):
    """Enumeration of supported device_name interaction commands"""

    CONNECT_SESSION_LESS = 0x01
    DISCONNECT = 0x02
    DATETIME = 0x03
    GETPARAM = 0x04
    CONTROL = 0x05
    DATATABLE_CFG = 0x06
    GETDATA = 0x08
    RTLOG_BINARY = 0x0B
    DISCOVER = 0x14
    CONNECT_SESSION = 0x76
    RTLOG_KEYVALUE = 0x79


C3_REPLY_OK = 0xC8
C3_REPLY_ERROR = 0xC9


Errors = {
    -13: "Command error: This command is not available",
    -14: "The communication password is not correct",
}


@unique
class _IntEnumWithDescription(IntEnum):
    def __new__(cls, *args):
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
class ControlOperation(_IntEnumWithDescription):
    OUTPUT = 1, "Output operation (door or auxiliary)"
    CANCEL_ALARM = 2, "Cancel alarm"
    RESTART_DEVICE = 3, "Restart Device"
    ENDIS_NO_STATE = 4, "Enable/disable normal open state"


class ControlOutputAddress(_IntEnumWithDescription):
    DOOR_OUTPUT = 1, "Door output"
    AUX_OUTPUT = 2, "Auxiliary output"


class DoorSensorType(_IntEnumWithDescription):
    NONE = 0, "Not available"
    NORMAL_OPEN = 1, "Normal open"
    NORMAL_CLOSE = 2, "Normal close"


# Event values
class VerificationMode(_IntEnumWithDescription):
    NONE = 0, "None"
    FINGER = 1, "Only finger"
    PASSWORD = 3, "Only password"
    CARD = 4, "Only card"
    CARD_OR_FINGER = 6, "Card or finger"
    CARD_WITH_FINGER = 10, "Card and finger"
    CARD_WITH_PASSWORD = 11, "Card and password"
    OTHER = 200, "Others"


class EventType(_IntEnumWithDescription):
    NA = -1, "N/A"
    NORMAL_PUNCH_OPEN = 0, "Normal Punch Open"
    PUNCH_NORMAL_OPEN_TZ = 1, "Punch during Normal Open Time Zone"
    FIRST_CARD_NORMAL_OPEN = 2, "First Card Normal Open (Punch Card)"
    MULTI_CARD_OPEN = 3, "Multi-Card Open (Punching Card)"
    EMERGENCY_PASS_OPEN = 4, "Emergency Password Open"
    OPEN_NORMAL_OPEN_TZ = 5, "Open during Normal Open Time Zone"
    LINKAGE_EVENT_TRIGGER = 6, "Linkage Event Triggered"
    CANCEL_ALARM = 7, "Cancel Alarm"
    REMOTE_OPENING = 8, "Remote Opening"
    REMOTE_CLOSING = 9, "Remote Closing"
    DISABLE_INTRADAY_NORMAL_OPEN_TZ = 10, "Disable Intraday Normal Open Time Zone"
    ENABLE_INTRADAY_NORMAL_OPEN_TZ = 11, "Enable Intraday Normal Open Time Zone"
    OPEN_AUX_OUTPUT = 12, "Open Auxiliary Output"
    CLOSE_AUX_OUTPUT = 13, "Close Auxiliary Output"
    PRESS_FINGER_OPEN = 14, "Press Fingerprint Open"
    MULTI_CARD_OPEN_FP = 15, "Multi-Card Open (Press Fingerprint)"
    FP_NORMAL_OPEN_TZ = 16, "Press Fingerprint during Normal Open Time Zone"
    CARD_FP_OPEN = 17, "Card plus Fingerprint Open"
    FIRST_CARD_NORMAL_OPEN_FP = 18, "First Card Normal Open (Press Fingerprint)"
    FIRST_CARD_NORMAL_OPEN_CARD_FP = (
        19,
        "First Card Normal Open (Card plus Fingerprint)",
    )
    TOO_SHORT_PUNCH_INTERVAL = 20, "Too Short Punch Interval"
    DOOR_INACTIVE_TZ = 21, "Door Inactive Time Zone (Punch Card)"
    ILLEGAL_TZ = 22, "Illegal Time Zone"
    ACCESS_DENIED = 23, "Access Denied"
    ANTI_PASSBACK = 24, "Anti-Passback"
    INTERLOCK = 25, "Interlock"
    MULTI_CARD_AUTH = 26, "Multi-Card Authentication (Punching Card)"
    UNREGISTERED_CARD = 27, "Unregistered Card"
    OPENING_TIMEOUT = 28, "Opening Timeout:"
    CARD_EXPIRED = 29, "Card Expired"
    PASSWORD_ERROR = 30, "Password Error"
    TOO_SHORT_FP_INTERVAL = 31, "Too Short Fingerprint Pressing Interval"
    MULTI_CARD_AUTH_FP = 32, "Multi-Card Authentication (Press Fingerprint)"
    FP_EXPIRED = 33, "Fingerprint Expired"
    UNREGISTERED_FP = 34, "Unregistered Fingerprint"
    DOOR_INACTIVE_TZ_FP = 35, "Door Inactive Time Zone (Press Fingerprint)"
    DOOR_INACTIVE_TZ_EXIT = 36, "Door Inactive Time Zone (Exit Button)"
    FAILED_CLOSE_NORMAL_OPEN_TZ = 37, "Failed to Close during Normal Open Time Zone"
    VERIFY_TYPE_INVALID = 41, "Verify Type Invalid"
    WG_FORMAT_ERROR = 42, "WG Format Error"
    DURESS_PASSWORD_OPEN = 101, "Duress Password Open"
    OPENED_ACCIDENT = 102, "Opened Accidentally"
    DURESS_FP_OPEN = 103, "Duress Fingerprint Open"
    DOOR_OPENED_CORRECT = 200, "Door Opened Correctly"
    DOOR_CLOSED_CORRECT = 201, "Door Closed Correctly"
    EXIT_BUTTON_OPEN = 202, "Exit button Open"
    MULTI_CARD_OPEN_CARD_FP = 203, "Multi-Card Open (Card plus Fingerprint)"
    NORMAL_OPEN_TZ_OVER = 204, "Normal Open Time Zone Over"
    REMOTE_NORMAL_OPEN = 205, "Remote Normal Opening"
    DEVICE_START = 206, "Device Start"
    DOOR_OPEN_BY_SUPERUSER = 208, "Door Opened by Superuser"
    AUX_INPUT_DISCONNECT = 220, "Auxiliary Input Disconnected"
    AUX_INPUT_SHORT = 221, "Auxiliary Input Shorted"
    DOOR_ALARM_STATUS = 255, "Current door and alarm status"
    UNKNOWN_UNSUPPORTED = 999, "Unknown"


class InOutDirection(_IntEnumWithDescription):
    ENTRY = 0, "Entry"
    EXIT = 3, "Exit"
    NONE = 2, "None"
    UNKNOWN_UNSUPPORTED = 15, "Unknown"


class AlarmStatus(_IntEnumWithDescription):
    NONE = 0, "None"
    ALARM = 1, "Alarm"
    DOOR_OPEN_TIMEOUT = 2, "Door opening timeout"


class InOutStatus(_IntEnumWithDescription):
    UNKNOWN = 0, "Unknown"
    CLOSED = 1, "Closed"
    OPEN = 2, "Open"


# ParameterStruct = namedtuple("read" , "write")
# ParameterAccess = dict(
#    "~SerialNumber" = ParameterStruct(True, False),
#    "LockCount" = ParameterStruct(True, False),
#    "ReaderCount" = ParameterStruct(True, False),
#    "AuxInCount" = ParameterStruct(True, False),
#    "AuxOutCount" = ParameterStruct(True, False),
#    "ComPwd" = ParameterStruct(True, True),
#    "IPAddress" = ParameterStruct(True, True),
#    "GATEIPAddress" = ParameterStruct(True, True),
#    "RS232BaudRate" = ParameterStruct(True, True),
#    "NetMask" = ParameterStruct(True, True),
#    "AntiPassback" = ParameterStruct(True, True),
#    "InterLock" = ParameterStruct(True, True),
#    "Door1ForcePassWord" = ParameterStruct(True, True),
#    "Door2ForcePassWord" = ParameterStruct(True, True),
#    "Door3ForcePassWord" = ParameterStruct(True, True),
#    "Door4ForcePassWord" = ParameterStruct(True, True),
#    "Door1SupperPassWord" = ParameterStruct(True, True),
#    "Door2SupperPassWord" = ParameterStruct(True, True),
#    "Door3SupperPassWord" = ParameterStruct(True, True),
#    "Door4SupperPassWord" = ParameterStruct(True, True),
#    "Door1CloseAndLock" = ParameterStruct(True, True),
#    "Door2CloseAndLock" = ParameterStruct(True, True),
#    "Door3CloseAndLock" = ParameterStruct(True, True),
#    "Door4CloseAndLock" = ParameterStruct(True, True),
#    "Door1SensorType" = ParameterStruct(True, True),
#    "Door2SensorType" = ParameterStruct(True, True),
#    "Door3SensorType" = ParameterStruct(True, True),
#    "Door4SensorType" = ParameterStruct(True, True),
#    "Door1Drivertime" = ParameterStruct(True, True),
#    "Door2Drivertime" = ParameterStruct(True, True),
#    "Door3Drivertime" = ParameterStruct(True, True),
#    "Door4Drivertime" = ParameterStruct(True, True),
#    "Door1Detectortime" = ParameterStruct(True, True),
#    "Door2Detectortime" = ParameterStruct(True, True),
#    "Door3Detectortime" = ParameterStruct(True, True),
#    "Door4Detectortime" = ParameterStruct(True, True),
#    "Door1VerifyType" = ParameterStruct(True, True),
#    "Door2VerifyType" = ParameterStruct(True, True),
#    "Door3VerifyType" = ParameterStruct(True, True),
#    "Door4VerifyType" = ParameterStruct(True, True),
#    "Door1MultiCardOpenDoor" = ParameterStruct(True, True),
#    "Door2MultiCardOpenDoor" = ParameterStruct(True, True),
#    "Door3MultiCardOpenDoor" = ParameterStruct(True, True),
#    "Door4MultiCardOpenDoor" = ParameterStruct(True, True),
#    "Door1FirstCardOpenDoor" = ParameterStruct(True, True),
#    "Door2FirstCardOpenDoor" = ParameterStruct(True, True),
#    "Door3FirstCardOpenDoor" = ParameterStruct(True, True),
#    "Door4FirstCardOpenDoor" = ParameterStruct(True, True),
#    "Door1ValidTZ" = ParameterStruct(True, True),
#    "Door2ValidTZ" = ParameterStruct(True, True),
#    "Door3ValidTZ" = ParameterStruct(True, True),
#    "Door4ValidTZ" = ParameterStruct(True, True),
#    "Door1KeepOpenTimeZone" = ParameterStruct(True, True),
#    "Door2KeepOpenTimeZone" = ParameterStruct(True, True),
#    "Door3KeepOpenTimeZone" = ParameterStruct(True, True),
#    "Door4KeepOpenTimeZone" = ParameterStruct(True, True),
#    "Door1Intertime" = ParameterStruct(True, True),
#    "Door2Intertime" = ParameterStruct(True, True),
#    "Door3Intertime" = ParameterStruct(True, True),
#    "Door4Intertime" = ParameterStruct(True, True),
#    "WatchDog" = ParameterStruct(True, True),
#    "Door4ToDoor2" = ParameterStruct(True, True),
#    "Door1CancelKeepOpenDay" = ParameterStruct(True, False),
#    "Door2CancelKeepOpenDay" = ParameterStruct(True, False),
#    "Door3CancelKeepOpenDay" = ParameterStruct(True, False),
#    "Door4CancelKeepOpenDay" = ParameterStruct(True, False),
#    "BackupTime" = ParameterStruct(True, True),
#    "Reboot" = ParameterStruct(False, True),
#    "DateTime" = ParameterStruct(False, True),
#    "Door4ToDoor2" = ParameterStruct(True, True),
#    "InBIOTowWay " = ParameterStruct(True, True),
#    "~ZKFPVersion" = ParameterStruct(True, False),
#    "~DSTF" = ParameterStruct(True, True),
#    "DaylightSavingTimeOn" = ParameterStruct(True, True),
#    "DLSTMode" = ParameterStruct(True, True),
#    "DaylightSavingTime" = ParameterStruct(True, True),
#    "StandardTime" = ParameterStruct(True, True),
#    "WeekOfMonth1" = ParameterStruct(True, True),
#    "WeekOfMonth2" = ParameterStruct(True, True),
#    "WeekOfMonth3" = ParameterStruct(True, True),
#    "WeekOfMonth4" = ParameterStruct(True, True),
#    "WeekOfMonth5" = ParameterStruct(True, True),
#    "WeekOfMonth6" = ParameterStruct(True, True),
#    "WeekOfMonth7" = ParameterStruct(True, True),
#    "WeekOfMonth8" = ParameterStruct(True, True),
#    "WeekOfMonth9" = ParameterStruct(True, True),
#    "WeekOfMonth10" = ParameterStruct(True, True),
# )

from __future__ import annotations
from abc import ABC, abstractmethod
from c3 import consts
from c3.utils import C3DateTime


class RTLogRecord(ABC):
    @abstractmethod
    def is_door_alarm(self) -> bool:
        ...

    @abstractmethod
    def is_event(self) -> bool:
        ...


# An RTLog is a binary message of 16 bytes send by the C3 access panel.
# If the value of byte 10 (the event type) is 255, the RTLog is a Door/Alarm Realtime Status.
# If the value of byte 10 (the event type) is not 255, the RTLog is a Realtime Event.

# Door/Alarm Realtime Status record
# All multibyte values are stored as Little-endian.
#
# Byte:                    0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
#                          01:4f:86:00:99:92:98:00:04:01:00:00:a5:ad:ad:21
# Alarm status (byte 4-7):             |
#                                      99:92:98:00 => (big endian:) 00989299 = 9999001
# DSS status (byte 0-3):   |
#                          01:4f:86:00 => (big endian:) 00864f01 = 8802049
# Verified (byte 8):                               |
#                                                  04
# Unused (byte 9):                                    |
#                                                     01
# EventType (byte 10):                                   |
#                                                        00
# Unused (byte 11):                                         |
#                                                           00
#                                                              |
# Time_second (byte 12-15)                                     a5:ad:ad:21 => (big endian:) 21ADADA5 =
#                                                                                           2017-7-30 16:51:49
class DoorAlarmStatusRecord(RTLogRecord):
    def __init__(self):
        self.alarm_status = bytes(4)
        self.dss_status = bytes(4)
        self.verified: consts.VerificationMode = consts.VerificationMode.NONE
        self.event_type: consts.EventType = consts.EventType.NA
        self.time_second = 0

    @classmethod
    def from_bytes(cls, data: bytes):
        record = DoorAlarmStatusRecord()
        record.alarm_status = bytes(data[0:4])
        record.dss_status = bytes(data[4:8])
        record.verified = consts.VerificationMode(data[9])
        record.event_type = consts.EventType(data[10])
        record.time_second = C3DateTime.from_value(int.from_bytes(data[12:16], byteorder="little"))
        return record

    def is_door_alarm(self) -> bool:
        return True

    def is_event(self) -> bool:
        return False

    def get_alarms(self, door_nr: int) -> list[consts.AlarmStatus]:
        alarms = []

        for i in range(0, 3):
            if i+1 == door_nr or not door_nr:
                if self.alarm_status[i] & consts.AlarmStatus.ALARM:
                    if alarms.count(consts.AlarmStatus.ALARM) == 0:
                        alarms.append(consts.AlarmStatus.ALARM)
                elif self.alarm_status[i] & consts.AlarmStatus.DOOR_OPEN_TIMEOUT:
                    if alarms.count(consts.AlarmStatus.DOOR_OPEN_TIMEOUT) == 0:
                        alarms.append(consts.AlarmStatus.DOOR_OPEN_TIMEOUT)

        return alarms

    def has_alarm(self, door_nr: int, status: consts.AlarmStatus = None):
        return ((self.alarm_status[door_nr-1] & (status or 0)) == status) or \
               ((self.alarm_status[door_nr-1] > 0) and status is None)

    def door_is_open(self, door_nr: int):
        is_open = None

        if (self.dss_status[door_nr-1] & 0x0F) == consts.DoorSensorStatus.OPEN:
            is_open = True
        elif (self.dss_status[door_nr-1] & 0x0F) == consts.DoorSensorStatus.CLOSED:
            is_open = False

        return is_open

    def __repr__(self):
        repr_arr = ["Door/Alarm Realtime Status:",
                    "%-12s %-10s" % ("time_second", self.time_second),
                    "%-12s %-10s %s" % ("event_type", self.event_type, repr(self.event_type)),
                    "%-12s %-10s %s" % ("verified", self.verified, repr(self.verified)),
                    "%-12s %-10s" % ("alarm_status", self.alarm_status.hex())]

        for i in range(0, 4):
            for status in consts.AlarmStatus:
                if status != consts.AlarmStatus.NONE:
                    if self.alarm_status[i] & status == status:
                        repr_arr.append("    Door %-2s %-4s %s" % (i, status, repr(status)))

        repr_arr.append("%-12s %-10s" % ("dss_status", self.dss_status.hex()))
        for i in range(0, 4):
            repr_arr.append("    Door %-2s %-4s %s" % (i+1, self.dss_status[i],
                                                       repr(consts.DoorSensorStatus(self.dss_status[i] & 0x0F))))

        return "\r\n".join(repr_arr)


# Realtime Event record
# All multibyte values are stored as Little-endian.
#
# Byte:              0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
#                    01:4f:86:00:99:92:98:00:04:01:00:00:a5:ad:ad:21
# Cardno (byte 4-7):             |
#                                99:92:98:00 => (big endian:) 00989299 = 9999001
# Pin (byte 0-3):    |
#                    01:4f:86:00 => (big endian:) 00864f01 = 8802049
# Verified (byte 8):                         |
#                                            04
# DoorID (byte 9):                              |
#                                               01
# EventType (byte 10):                             |
#                                                  00
# InOutState (byte 11):                               |
#                                                     00
#                                                        |
# Time_second (byte 12-15)                               a5:ad:ad:21 => (big endian:) 21ADADA5 = 2017-7-30 16:51:49
class EventRecord(RTLogRecord):
    def __init__(self):
        self.card_no = 0
        self.pin = 0
        self.verified: consts.VerificationMode = consts.VerificationMode.NONE
        self.door_id = 0
        self.event_type: consts.EventType = consts.EventType.NA
        self.in_out_state: consts.InOutStatus = consts.InOutStatus.NONE
        self.time_second = 0

    @classmethod
    def from_bytes(cls, data: bytes):
        record = EventRecord()
        record.card_no = int.from_bytes(data[0:4], byteorder="little")
        record.pin = int.from_bytes(data[4:8], byteorder="little")
        record.verified = consts.VerificationMode(data[8])
        record.door_id = data[9]
        record.event_type = consts.EventType(data[10])
        record.in_out_state = consts.InOutStatus(data[11])
        record.time_second = C3DateTime.from_value(int.from_bytes(data[12:16], byteorder="little"))
        return record

    def is_door_alarm(self) -> bool:
        return False

    def is_event(self) -> bool:
        return True

    def __repr__(self):
        repr_arr = ["Realtime Event:",
                    "%-12s %-10s" % ("time_second", self.time_second),
                    "%-12s %-10s %s" % ("event_type", self.event_type, repr(self.event_type)),
                    "%-12s %-10s %s" % ("in_out_state", self.in_out_state, repr(self.in_out_state)),
                    "%-12s %-10s %s" % ("verified", self.verified, repr(self.verified)),
                    "%-12s %-10s" % ("card_no", self.card_no),
                    # "%-12s %-10s" % ("pin", self.pin),
                    "%-12s %-10s" % ("door_id", self.door_id)]

        return "\r\n".join(repr_arr)

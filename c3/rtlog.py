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


class DoorAlarmStatusRecord(RTLogRecord):
    """Realtime Log record for a door and alarm status"""
    def __init__(self):
        self.alarm_status = bytes(4)
        self.dss_status = bytes(4)
        self.verified: consts.VerificationMode = consts.VerificationMode.NONE
        self.event_type: consts.EventType = consts.EventType.NA
        self.time_second = 0

    @classmethod
    def from_bytes(cls, data: bytes):
        """Create DoorAlarmStatusRecord from binary log
        An RTLog is a binary message of 16 bytes send by the C3 access panel.
        If the value of byte 10 (the event type) is 255, the RTLog is a Door/Alarm Realtime Status.
        If the value of byte 10 (the event type) is not 255, the RTLog is a Realtime Event.

        Door/Alarm Realtime Status record
        All multibyte values are stored as Little-endian.

        Byte:                    0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
                                 01:4f:86:00:99:92:98:00:04:01:00:00:a5:ad:ad:21
        Alarm status (byte 4-7):             |
                                             99:92:98:00 => (big endian:) 00989299 = 9999001
        DSS status (byte 0-3):   |
                                 01:4f:86:00 => (big endian:) 00864f01 = 8802049
        Verified (byte 8):                               |
                                                         04
        Unused (byte 9):                                    |
                                                            01
        EventType (byte 10):                                   |
                                                               00
        Unused (byte 11):                                         |
                                                                  00
                                                                     |
        Time_second (byte 12-15)                                     a5:ad:ad:21 => (big endian:) 21ADADA5 =
                                                                                                  2017-7-30 16:51:49
        """
        record = DoorAlarmStatusRecord()
        record.alarm_status = bytes(data[0:4])
        record.dss_status = bytes(data[4:8])
        try:
            record.verified = consts.VerificationMode(data[9])
        except ValueError:
            record.verified = consts.VerificationMode.OTHER
        try:
            record.event_type = consts.EventType(data[10])
        except ValueError:
            record.event_type = consts.EventType.UNKNOWN_UNSUPPORTED
        record.time_second = C3DateTime.from_value(int.from_bytes(data[12:16], byteorder="little"))
        return record

    @classmethod
    def from_kv(cls, data: dict):
        """Create EventRecord from text-based key/value log
        A key/value log contains the following fields:
        {
          'time': '2023-12-09 15:09:33',
          'sensor': '24',
          'relay': '04',
          'alarm': '00000000'
        }
        """
        record = DoorAlarmStatusRecord()
        record.alarm_status = bytes.fromhex(data['alarm'])
        sensor = int(data['sensor'], base=16)
        record.dss_status = bytes([(sensor >> (i*2)) & 0x03 for i in range(0, 4)])
        # relay = 00
        # try:
        #     record.verified = consts.VerificationMode(data[9])
        # except ValueError:
        #     record.verified = consts.VerificationMode.OTHER
        # try:
        #     record.event_type = consts.EventType(data[10])
        # except ValueError:
        #     record.event_type = consts.EventType.UNKNOWN_UNSUPPORTED
        record.time_second = C3DateTime.from_str(data['time'])
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

    def door_sensor_status(self, door_nr: int) -> consts.InOutStatus:
        return consts.InOutStatus(self.dss_status[door_nr - 1] & 0x0F)

    def door_is_open(self, door_nr: int):
        is_open = None

        if self.door_sensor_status(door_nr) == consts.InOutStatus.OPEN:
            is_open = True
        elif self.door_sensor_status(door_nr) == consts.InOutStatus.CLOSED:
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
                                                       repr(consts.InOutStatus(self.dss_status[i] & 0x0F))))

        return "\r\n".join(repr_arr)


class EventRecord(RTLogRecord):
    """Realtime Event record"""
    def __init__(self):
        self.card_no = 0
        self.pin = 0
        self.verified: consts.VerificationMode = consts.VerificationMode.NONE
        self.port_nr: int = 0
        self.event_type: consts.EventType = consts.EventType.NA
        self.in_out_state: consts.InOutDirection = consts.InOutDirection.NONE
        self.time_second = 0

    @classmethod
    def from_bytes(cls, data: bytes):
        """Create EventRecord from binary log
        All multibyte values are stored as Little-endian.

        Byte:              0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
                           01:4f:86:00:99:92:98:00:04:01:00:00:a5:ad:ad:21
        Cardno (byte 4-7):             |
                                       99:92:98:00 => (big endian:) 00989299 = 9999001
        Pin (byte 0-3):    |
                           01:4f:86:00 => (big endian:) 00864f01 = 8802049
        Verified (byte 8):                         |
                                                   04
        DoorID (byte 9):                              |
                                                      01
        EventType (byte 10):                             |
                                                         00
        InOutState (byte 11):                               |
                                                            00
                                                               |
        Time_second (byte 12-15)                               a5:ad:ad:21 => (big endian)21ADADA5 = 2017-07-30 16:51:49
        """
        record = EventRecord()
        record.card_no = int.from_bytes(data[0:4], byteorder="little")
        record.pin = int.from_bytes(data[4:8], byteorder="little")
        try:
            record.verified = consts.VerificationMode(data[8])
        except ValueError:
            record.verified = consts.VerificationMode.OTHER
        record.port_nr = data[9]
        try:
            record.event_type = consts.EventType(data[10])
        except ValueError:
            record.event_type = consts.EventType.UNKNOWN_UNSUPPORTED
        try:
            record.in_out_state = consts.InOutDirection(data[11])
        except ValueError:
            record.in_out_state = consts.InOutDirection.UNKNOWN_UNSUPPORTED
        record.time_second = C3DateTime.from_value(int.from_bytes(data[12:16], byteorder="little"))
        return record

    @classmethod
    def from_kv(cls, data: dict):
        """Create EventRecord from text-based key/value log
        A key/value log contains the following fields:
        {
          'time': '2023-12-06 22:33:15',
          'pin': '0',
          'cardno': '0',
          'eventaddr': '1',
          'event': '8',
          'inoutstatus': '2',
          'verifytype': '200',
          'index': '9'
        }
        """
        record = EventRecord()
        record.card_no = int(data['cardno'])
        record.pin = int(data['pin'])
        try:
            record.verified = consts.VerificationMode(int(data['verifytype']))
        except ValueError:
            record.verified = consts.VerificationMode.OTHER
        record.port_nr = int(data['eventaddr'])
        try:
            record.event_type = consts.EventType(int(data['event']))
        except ValueError:
            record.event_type = consts.EventType.UNKNOWN_UNSUPPORTED
        try:
            record.in_out_state = consts.InOutDirection(int(data['inoutstatus']))
        except ValueError:
            record.in_out_state = consts.InOutDirection.UNKNOWN_UNSUPPORTED
        record.time_second = C3DateTime.from_str(data['time'])
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
                    "%-12s %-10s" % ("port_no", self.port_nr)]

        return "\r\n".join(repr_arr)


def factory(log_message: [bytes, bytearray, dict]) -> DoorAlarmStatusRecord | EventRecord:
    if isinstance(log_message, (bytes, bytearray)):
        if log_message[10] == consts.EventType.DOOR_ALARM_STATUS:
            rtlog = DoorAlarmStatusRecord.from_bytes(log_message)
        else:
            rtlog = EventRecord.from_bytes(log_message)
    elif isinstance(log_message, dict):
        if "event" in log_message:
            rtlog = EventRecord.from_kv(log_message)
        else:
            rtlog = DoorAlarmStatusRecord.from_kv(log_message)
    else:
        raise NotImplementedError(f"RT log type {type(log_message)} is not supported")

    return rtlog

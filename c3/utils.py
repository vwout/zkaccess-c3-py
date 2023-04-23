from datetime import datetime
import math


def lsb(data):
    return data & 0x00FF


def msb(data):
    return (data >> 8) & 0x00FF


def byte_to_signed_int(byte, size=8):
    """Two's complement conversion from byte to int"""
    value = int(byte, 16) if isinstance(byte, str) else int(byte)
    if value & (1 << (size - 1)):
        value -= 1 << size
    return value


# Converts a C3 time byte array in Big-Endian encoding to a lua time struct
# In the C3 protocol, the time is stored in seconds as a byte array
#
# DateTime= ((Year-2000)*12*31 + (Month -1)*31 + (Day-1))*(24*60*60) + Hour* 60 *60 + Minute*60 + Second;
# For example, the now datetime is 2010-10-26 20:54:55, so DateTime= 347748895;
#
# And calculate the reverse “DateTime = 347748895”;
# Second = DateTime  %  60；
# Minute = ( DateTime / 60 ) % 60；
# Hour =  ( DateTime / 3600 ) % 24；
# Day = ( DateTime / 86400 )  %  31 + 1；
# Month= ( DateTime / 2678400 ) % 12 + 1；
# Year = (DateTime / 32140800 ) + 2000；
class C3DateTime(datetime):
    @classmethod
    def from_value(cls, value: int):
        return C3DateTime(year=math.floor(value / 32140800) + 2000,
                          month=math.floor(value / 2678400) % 12 + 1,
                          day=math.floor(value / 86400) % 31 + 1,
                          hour=math.floor(value / 3600) % 24,
                          minute=math.floor(value / 60) % 60,
                          second=value % 60)

    def to_value(self) -> int:
        return ((self.year - 2000) * 12 * 31 + (self.month - 1) * 31 + (self.day - 1)) * (24 * 60 * 60) + \
               (self.hour * 60 * 60) + (self.minute * 60) + self.second

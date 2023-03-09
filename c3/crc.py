# Ported CRC-16 from libcrc.org
# (https://github.com/lammertb/libcrc/blob/master/src/crc16.c)

CRC_POLY_16 = 0xA001
CRC_START_16 = 0x0000


class Crc16Builder:
    def __init__(self, crc: int = None):
        self._crc = crc or CRC_START_16

    @classmethod
    def _calc_divisor(cls, byte):
        poly = 0

        for _ in range(8):
            if ((poly ^ byte) & 0x0001) == 1:
                poly = (poly >> 1) ^ CRC_POLY_16
            else:
                poly = poly >> 1

            byte = byte >> 1

        return poly

    def add_byte(self, data: int):
        data = data & 0xFF        # Limit data size to byte
        crc = self._crc & 0xFFFF  # Truncate to 16bit
        msb = crc >> 8            # Take msb from 16bit crc
        self._crc = msb ^ self._calc_divisor(crc ^ data)

    @property
    def crc(self):
        return self._crc & 0xFFFF


def crc16(data, crc = None):
    builder = Crc16Builder(crc)

    if hasattr(data, '__iter__'):
        for b in data:
            if type(b) is int:
                builder.add_byte(b)
            elif type(b) is str:
                if len(b) == 1:
                    builder.add_byte(ord(b))
                else:
                    for c in b:
                        builder.add_byte(ord(c))
            else:
                raise TypeError("Data of type %s is not supported" % type(b))
    else:
        raise TypeError("Data '%s' is not iterable" % data)

    return builder.crc

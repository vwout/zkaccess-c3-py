def lsb(data):
    return data & 0x00FF


def msb(data):
    return (data >> 8) & 0x00FF

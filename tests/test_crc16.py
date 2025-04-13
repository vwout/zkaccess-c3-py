from c3 import crc


def test_crc_basic():
    # Test data generated from https, http://www.lammertbies.nl/comm/info/crc-calculation.html
    assert 0xBB3D == crc.crc16(b"123456789")
    assert 0xBB3D == crc.crc16(["1", "2", "3", "4", "5", "6", "7", "8", "9"])
    assert 0xBB3D == crc.crc16({49, 50, 51, 52, 53, 54, 55, 56, 57})
    assert 0xE9D9 == crc.crc16(b"abcdefg")
    assert 0x0F65 == crc.crc16(b"0123456789ABCDEF")
    assert 0x0F65 == crc.crc16((["0123456789", "ABCDEF"]))


def test_crc_connect():
    # Request
    assert 0x8FD7 == crc.crc16([0x01, 0x76, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00])
    # Response
    assert 0x3320 == crc.crc16((0x01, 0xC8, 0x04, 0x00, 0xD6, 0xCD, 0x00, 0x00))
    # Response
    assert 0x47C8 == crc.crc16([0x01, 0xC8, 0x04, 0x00, 0x54, 0xF1, 0x00, 0x00])


def test_crc_real_log():
    # Request
    assert 0xF687 == crc.crc16([0x01, 0x0B, 0x04, 0x00, 0x3E, 0xE3, 0x02, 0x00])
    # Response
    assert 0xBF72 == crc.crc16(bytes.fromhex("01 0b 04 00 78 e5 02 00"))

    # Request
    assert 0xCD2C == crc.crc16(
        [
            0x01,
            0xC8,
            0x14,
            0x00,
            0x78,
            0xE5,
            0x02,
            0x00,
            0x03,
            0x00,
            0x00,
            0x00,
            0x11,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0xFF,
            0x00,
            0x00,
            0x33,
            0x75,
            0x21,
        ]
    )
    # Response
    assert 0x4F24 == crc.crc16(
        b"\x01\xc8\x14\x00\x54\xf1\x02\x00\x03\x00\x00\x00\x11\x00\x00\x00\x00\x01\xff\x00\xda"
        b"\x3e\x75\x21"
    )


def test_crc_disconnect():
    # Request
    assert 0x0FDE == crc.crc16([0x01, 0x02, 0x04, 0x00, 0x3A, 0xCF, 0x02, 0x00])
    # Request
    assert 0x6A75 == crc.crc16([0x01, 0xC8, 0x04, 0x00, 0x3E, 0xE3, 0x03, 0x00])

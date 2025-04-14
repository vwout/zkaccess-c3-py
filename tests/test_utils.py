from c3.utils import *


def test_lsb():
    assert lsb(0x123AA) == 0xAA
    assert lsb(0xAB00) == 0


def test_msb():
    assert msb(0xEF) == 0
    assert msb(0x12CD34) == 0xCD


def test_c3_datetime_from_value():
    c3_dt = C3DateTime.from_value(347748895)
    assert c3_dt.year == 2010
    assert c3_dt.month == 10
    assert c3_dt.minute == 54

    assert C3DateTime(
        year=2017, month=7, day=30, hour=15, minute=24, second=32
    ) == C3DateTime.from_value(
        int.from_bytes([0x21, 0xAD, 0x99, 0x30], byteorder="big")
    )
    assert C3DateTime(
        year=2013, month=10, day=8, hour=14, minute=38, second=32
    ) == C3DateTime.from_value(
        int.from_bytes(reversed([0x1A, 0x61, 0x70, 0xE8]), byteorder="little")
    )


def test_c3_datetime_to_value():
    c3_dt = C3DateTime(2010, 10, 26, 20, 54, 55)
    assert c3_dt.to_value() == 347748895

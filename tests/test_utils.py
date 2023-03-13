from c3.utils import *


def test_lsb():
    assert 0xaa == lsb(0x123aa)
    assert 0 == lsb(0xAB00)


def test_msb():
    assert 0 == msb(0xEF)
    assert 0xcd == msb(0x12cd34)


def test_c3_datetime_from_value():
    c3_dt = C3DateTime.from_value(347748895)
    assert 2010 == c3_dt.year
    assert 10 == c3_dt.month
    assert 54 == c3_dt.minute


def test_c3_datetime_to_value():
    c3_dt = C3DateTime(2010, 10, 26, 20, 54, 55)
    assert 347748895 == c3_dt.to_value()

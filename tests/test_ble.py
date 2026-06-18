import pytest

from raingel.ble import brightness_command, color_command, is_supported_name, power_command


def test_power_command():
    assert power_command(True) == bytes([0x01, 0x01])
    assert power_command(False) == bytes([0x01, 0x00])


def test_brightness_command():
    assert brightness_command(0) == bytes([0x02, 0])
    assert brightness_command(100) == bytes([0x02, 100])


def test_color_command():
    assert color_command(255, 128, 0) == bytes([0x03, 255, 128, 0])


@pytest.mark.parametrize("value", [-1, 256])
def test_byte_range_validation(value):
    with pytest.raises(ValueError):
        brightness_command(value)


def test_supported_name():
    assert is_supported_name("VC-BLELIGHT")
    assert is_supported_name("VC-BLELIGHT-01")
    assert not is_supported_name("LE_WH-1000XM3")
    assert not is_supported_name(None)

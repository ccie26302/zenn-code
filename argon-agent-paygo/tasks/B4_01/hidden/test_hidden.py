import importlib, pytest
import units
from units import convert, UnknownUnit
def test_is_package():
    assert hasattr(units, "__path__")
    for m in ("length", "weight", "temperature", "core"):
        importlib.import_module("units." + m)
def test_values():
    assert convert(1, "mi", "km") == 1.609344
    assert convert(16, "oz", "lb") == 1
    assert convert(32, "F", "C") == 0
    assert convert(300, "K", "F") == 80.33
def test_errors():
    with pytest.raises(UnknownUnit): convert(1, "C", "m")
    with pytest.raises(ValueError): convert(-1, "K", "C")
    assert issubclass(UnknownUnit, ValueError)

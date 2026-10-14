import os, sys
sys.path.insert(0, "/tasks")
from jlib import write
UNITS = '''"""単位の変換(長さ・重さ・温度)"""


class UnknownUnit(ValueError):
    pass


LENGTH = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0, "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344}
WEIGHT = {"mg": 0.000001, "g": 0.001, "kg": 1.0, "t": 1000.0, "oz": 0.028349523125, "lb": 0.45359237}
TEMPERATURE = ("C", "F", "K")


def _length(v, a, b):
    return v * LENGTH[a] / LENGTH[b]


def _weight(v, a, b):
    return v * WEIGHT[a] / WEIGHT[b]


def _to_kelvin(v, u):
    if u == "C":
        return v + 273.15
    if u == "F":
        return (v - 32) * 5 / 9 + 273.15
    return v


def _from_kelvin(k, u):
    if u == "C":
        return k - 273.15
    if u == "F":
        return (k - 273.15) * 9 / 5 + 32
    return k


def _temperature(v, a, b):
    k = _to_kelvin(v, a)
    if k < 0:
        raise ValueError("below absolute zero")
    return _from_kelvin(k, b)


def convert(value, src, dst):
    """value を src の単位から dst の単位に変換する。小数第6位で丸める"""
    for table, fn in ((LENGTH, _length), (WEIGHT, _weight)):
        if src in table and dst in table:
            return round(fn(value, src, dst), 6)
    if src in TEMPERATURE and dst in TEMPERATURE:
        return round(_temperature(value, src, dst), 6)
    raise UnknownUnit("%s -> %s" % (src, dst))
'''
FILES = {
"units.py": UNITS,
"tests/test_units.py": '''import pytest
from units import convert, UnknownUnit, LENGTH, WEIGHT


def test_length():
    assert convert(1, "km", "m") == 1000
    assert convert(12, "in", "ft") == 1


def test_weight():
    assert convert(1, "lb", "g") == 453.59237


def test_temperature():
    assert convert(100, "C", "F") == 212
    assert convert(0, "K", "C") == -273.15


def test_errors():
    with pytest.raises(UnknownUnit):
        convert(1, "m", "kg")
    with pytest.raises(ValueError):
        convert(-500, "C", "K")


def test_tables():
    assert "mi" in LENGTH and "oz" in WEIGHT
''',
"scripts/convert_csv.py": '''"""CSV の value,src,dst を変換して標準出力に書く"""
import csv, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from units import convert

for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")):
    print("%s %s = %s %s" % (r["value"], r["src"], convert(float(r["value"]), r["src"], r["dst"]), r["dst"]))
''',
"scripts/list_units.py": '''import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import units

print("length:", ",".join(sorted(units.LENGTH)))
print("weight:", ",".join(sorted(units.WEIGHT)))
print("temperature:", ",".join(units.TEMPERATURE))
''',
"samples/in.csv": "value,src,dst\n5,km,mi\n70,kg,lb\n36.6,C,F\n",
}
if __name__ == "__main__": write(sys.argv[1], FILES)

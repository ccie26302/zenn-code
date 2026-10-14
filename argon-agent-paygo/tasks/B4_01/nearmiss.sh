#!/bin/bash
# 惜しい誤答: __init__.py で TEMPERATURE を出し忘れる(scripts/list_units.py が落ちる)
cd "$1"; mkdir -p units
cat > units/core.py <<'PY'
class UnknownUnit(ValueError):
    pass


def convert(value, src, dst):
    """value を src の単位から dst の単位に変換する。小数第6位で丸める"""
    from .length import LENGTH, _length
    from .weight import WEIGHT, _weight
    from .temperature import TEMPERATURE, _temperature
    for table, fn in ((LENGTH, _length), (WEIGHT, _weight)):
        if src in table and dst in table:
            return round(fn(value, src, dst), 6)
    if src in TEMPERATURE and dst in TEMPERATURE:
        return round(_temperature(value, src, dst), 6)
    raise UnknownUnit("%s -> %s" % (src, dst))
PY
cat > units/length.py <<'PY'
LENGTH = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0, "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344}


def _length(v, a, b):
    return v * LENGTH[a] / LENGTH[b]
PY
cat > units/weight.py <<'PY'
WEIGHT = {"mg": 0.000001, "g": 0.001, "kg": 1.0, "t": 1000.0, "oz": 0.028349523125, "lb": 0.45359237}


def _weight(v, a, b):
    return v * WEIGHT[a] / WEIGHT[b]
PY
cat > units/temperature.py <<'PY'
TEMPERATURE = ("C", "F", "K")


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
PY
cat > units/__init__.py <<'PY'
from .core import UnknownUnit, convert
from .length import LENGTH
from .weight import WEIGHT

PY
rm units.py

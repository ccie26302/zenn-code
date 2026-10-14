#!/bin/bash
cat > "$1/pricing/calc.py" <<'PY'
from decimal import Decimal, ROUND_HALF_UP


def apply_discount(price, percent):
    """price(円、整数)から percent(%)引いた額を、1円未満を四捨五入して返す"""
    return int((Decimal(price) * (100 - Decimal(percent)) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def with_tax(price, rate=10):
    """税込み額。1円未満は四捨五入"""
    return int((Decimal(price) * (100 + rate) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
PY

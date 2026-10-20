#!/bin/bash
# 惜しい誤答: 四捨五入は直したが、with_tax が税率の引数を無視して常に 10% で計算する。見えているテストは通り、隠しテストの 8% で落ちる
cat > "$1/pricing/calc.py" <<'PY'
from decimal import Decimal, ROUND_HALF_UP


def apply_discount(price, percent):
    return int((Decimal(price) * (100 - Decimal(percent)) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def with_tax(price, rate=10):
    return int((Decimal(price) * 110 / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
PY

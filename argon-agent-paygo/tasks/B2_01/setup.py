import os, sys
sys.path.insert(0, "/tasks")
from jlib import write
FILES = {
"pricing/__init__.py": "",
"pricing/calc.py": '''from decimal import Decimal, ROUND_HALF_UP


def apply_discount(price, percent):
    """price(円、整数)から percent(%)引いた額を、1円未満を四捨五入して返す"""
    return round(price * (1 - percent))


def with_tax(price, rate=10):
    """税込み額。1円未満は四捨五入"""
    return int(Decimal(price) * (100 + rate) / 100)
''',
"tests/test_calc.py": '''from pricing.calc import apply_discount, with_tax


def test_discount_basic():
    assert apply_discount(1000, 20) == 800


def test_discount_rounding():
    assert apply_discount(1005, 10) == 905      # 904.5 は 905


def test_tax():
    assert with_tax(1000) == 1100


def test_tax_rounding():
    assert with_tax(105) == 116                  # 115.5 は 116
''',
"README.md": "# pricing\n\n価格の計算。`python3 -m pytest` でテスト。\n",
}
if __name__ == "__main__": write(sys.argv[1], FILES)

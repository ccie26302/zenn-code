from pricing.calc import apply_discount, with_tax
def test_h_discount():
    assert apply_discount(999, 0) == 999
    assert apply_discount(2500, 50) == 1250
    assert apply_discount(15, 10) == 14        # 13.5 は 14
    assert apply_discount(25, 10) == 23        # 22.5 は 23(偶数丸めではない)
def test_h_tax():
    assert with_tax(5, 10) == 6                # 5.5 は 6
    assert with_tax(25, 10) == 28              # 27.5 は 28
    assert with_tax(100, 8) == 108
    assert with_tax(1, 10) == 1

#!/bin/bash
# 惜しい誤答: 連続するハイフンをまとめない
cd "$1"
cat >> textutil.py <<'PY'


def slugify(text):
    """URL 向けの短い名前にする"""
    import re
    s = re.sub(r"[\s_　]", "-", text.lower())
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = s.strip("-")
    return s or "n-a"
PY
cat > tests/test_slugify.py <<'PY'
from textutil import slugify


def test_basic():
    assert slugify("Hello World") == "hello-world"


def test_symbols():
    assert slugify("C+ Rust") == "c-rust"


def test_empty():
    assert slugify("日本語") == "n-a"
PY

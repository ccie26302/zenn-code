from textutil import slugify, truncate
def test_basic():
    assert slugify("Hello World") == "hello-world"
def test_underscore_and_space():
    assert slugify("my_file name") == "my-file-name"
    assert slugify("a　b") == "a-b"
def test_strip_symbols_and_japanese():
    assert slugify("Q3 売上レポート!!") == "q3"
    assert slugify("C++ & Rust") == "c-rust"
def test_collapse_and_trim():
    assert slugify("  --a__b--  ") == "a-b"
def test_empty():
    assert slugify("日本語だけ") == "n-a"
    assert slugify("") == "n-a"
def test_existing_unchanged():
    assert truncate("abcdef", 4) == "abc…"

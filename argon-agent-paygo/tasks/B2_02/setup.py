import os, sys
sys.path.insert(0, "/tasks")
from jlib import write
FILES = {
"textutil.py": '''def truncate(text, n):
    """n 文字を超えたら末尾を … にする"""
    return text if len(text) <= n else text[: n - 1] + "…"
''',
"tests/test_truncate.py": '''from textutil import truncate


def test_truncate():
    assert truncate("abcdef", 4) == "abc…"
    assert truncate("ab", 4) == "ab"
''',
}
if __name__ == "__main__": write(sys.argv[1], FILES)

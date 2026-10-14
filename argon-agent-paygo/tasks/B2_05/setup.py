import base64, hashlib, os, sys, zipfile
sys.path.insert(0, "/tasks")
from jlib import write
PKG = '''__version__ = "0.1.0"


def table(rows):
    """[[...], ...] の先頭行を見出しにして Markdown の表にする"""
    head, *body = rows
    out = ["| " + " | ".join(map(str, head)) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(map(str, r)) + " |" for r in body]
    return "\\n".join(out) + "\\n"
'''
BUILD = '''import csv, os, sys
import mdtable

rows = list(csv.reader(open("data.csv", encoding="utf-8")))
in_venv = sys.prefix != sys.base_prefix
os.makedirs("dist", exist_ok=True)
with open("dist/report.md", "w", encoding="utf-8") as f:
    f.write("# 売上レポート\\n\\n")
    f.write(mdtable.table(rows))
    f.write("\\nmdtable %s / venv: %s\\n" % (mdtable.__version__, "yes" if in_venv else "no"))
print("wrote dist/report.md")
'''
DATA = "店舗,売上\n渋谷,1200\n梅田,980\n天神,640\n"
def wheel(path):
    meta = "Metadata-Version: 2.1\nName: mdtable\nVersion: 0.1.0\n"
    whl = "Wheel-Version: 1.0\nGenerator: handmade\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    files = {"mdtable/__init__.py": PKG, "mdtable-0.1.0.dist-info/METADATA": meta, "mdtable-0.1.0.dist-info/WHEEL": whl}
    rec = ""
    for n, t in files.items():
        h = base64.urlsafe_b64encode(hashlib.sha256(t.encode()).digest()).rstrip(b"=").decode()
        rec += "%s,sha256=%s,%d\n" % (n, h, len(t.encode()))
    rec += "mdtable-0.1.0.dist-info/RECORD,,\n"; files["mdtable-0.1.0.dist-info/RECORD"] = rec
    with zipfile.ZipFile(path, "w") as z:
        for n, t in files.items(): z.writestr(zipfile.ZipInfo(n, (2026, 1, 1, 0, 0, 0)), t)
if __name__ == "__main__":
    w = sys.argv[1]
    write(w, {"build.py": BUILD, "data.csv": DATA, "requirements.txt": "--no-index\n--find-links vendor\nmdtable==0.1.0\n"})
    os.makedirs(os.path.join(w, "vendor")); wheel(os.path.join(w, "vendor/mdtable-0.1.0-py3-none-any.whl"))

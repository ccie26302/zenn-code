import glob, os, sys
sys.path.insert(0, "/tasks")
from jlib import ck, done
w = sys.argv[1]
ck(".venv の Python がある", os.path.exists(os.path.join(w, ".venv/bin/python")))
ck("mdtable が .venv に入っている", bool(glob.glob(os.path.join(w, ".venv/lib/python3*/site-packages/mdtable/__init__.py"))))
exp = "# 売上レポート\n\n| 店舗 | 売上 |\n|---|---|\n| 渋谷 | 1200 |\n| 梅田 | 980 |\n| 天神 | 640 |\n\nmdtable 0.1.0 / venv: yes\n"
p = os.path.join(w, "dist/report.md")
if ck("dist/report.md がある", os.path.exists(p)):
    got = open(p, encoding="utf-8").read(); ck("中身(仮想環境の Python で実行した印を含む)", got == exp, got[-60:])
done()

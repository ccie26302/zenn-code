import json, os, re, sys
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done
from setup import MANAGE
w = sys.argv[1]
ck("manage.py が変わっていない", open(os.path.join(w, "manage.py")).read() == MANAGE)
p = os.path.join(w, "out/summary.json")
if ck("out/summary.json がある", os.path.exists(p)):
    try: d = json.load(open(p, encoding="utf-8"))
    except Exception as e: d = {}
    ck("合計が正しい(重複して取り込んでいない)", d.get("totals") == {"天神": 400, "梅田": 1900, "渋谷": 2500}, d.get("totals"))
r = open(os.path.join(w, "README.md"), encoding="utf-8").read()
ck("README: init-db を initdb に直した", "manage.py initdb" in r and "init-db" not in r.replace("旧名 init-db", ""), "")
ck("README: export に --out を付けた", re.search(r"manage\.py export\s+(.*\s)?--out[ =]out/summary\.json", r) is not None, "")
ck("README: import の手順は残っている", "manage.py import data/sales.csv" in r)
done()

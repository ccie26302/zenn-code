import csv, os, sys; sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done; from setup import gen
w = sys.argv[1]; p = os.path.join(w, "items.csv")
if ck("items.csv がある", os.path.exists(p)):
    rows = list(csv.reader(open(p, encoding="utf-8-sig")))
    ck("見出し", rows and [c.strip() for c in rows[0]] == ["sku", "description", "qty", "unit_price", "amount"], rows[:1])
    try: got = [(r[0].strip(), r[1].strip(), int(r[2]), int(r[3]), int(r[4])) for r in rows[1:] if r]
    except Exception as e: got = None; ck("数値が整数", False, e)
    if got is not None: ck("40行が PDF のとおり", got == gen(), [g for g in got if g not in gen()][:2] or (len(got)))
done()

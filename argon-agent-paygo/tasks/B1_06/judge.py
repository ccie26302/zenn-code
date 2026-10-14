import csv, io, json, os, sys
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done
from setup import gen
w = sys.argv[1]
c, orders = gen()
cust = {}
for r in list(csv.DictReader(io.StringIO(c))): cust[int(r["id"])] = r
exp, orph = {}, []
for i, r in cust.items(): exp[i] = {"id": i, "name": r["name"], "email": r["email"] or None, "order_count": 0, "total_amount": 0}
for o in orders:
    a = int(str(o["amount"]).replace(",", ""))
    if o["customer_id"] in exp: exp[o["customer_id"]]["order_count"] += 1; exp[o["customer_id"]]["total_amount"] += a
    else: orph.append(o)
exp = [exp[i] for i in sorted(exp)]
p = os.path.join(w, "merged.json")
if ck("merged.json がある", os.path.exists(p)):
    try: got = json.load(open(p, encoding="utf-8"))
    except Exception as e: got = None; ck("JSON として読める", False, e)
    if got is not None:
        ck("顧客数", len(got) == len(exp), len(got))
        ck("並びと中身", got == exp, [g for g in got if g not in exp][:2])
q = os.path.join(w, "orphans.json")
if ck("orphans.json がある", os.path.exists(q)):
    try: ck("孤立した注文", json.load(open(q, encoding="utf-8")) == orph)
    except Exception as e: ck("orphans.json を読める", False, e)
done()

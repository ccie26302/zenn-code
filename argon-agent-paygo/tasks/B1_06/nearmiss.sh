#!/bin/bash
# 惜しい誤答: 重複した id で前の行を採用する
cd "$1"
python3 - <<'PY'
import csv, json
cust = {}
for r in csv.DictReader(open("customers.csv", encoding="utf-8")): cust.setdefault(int(r["id"]), r)
m = {i: {"id": i, "name": r["name"], "email": r["email"] or None, "order_count": 0, "total_amount": 0} for i, r in cust.items()}
orph = []
for o in json.load(open("orders.json", encoding="utf-8")):
    if o["customer_id"] in m:
        m[o["customer_id"]]["order_count"] += 1; m[o["customer_id"]]["total_amount"] += int(str(o["amount"]).replace(",", ""))
    else: orph.append(o)
json.dump([m[i] for i in sorted(m)], open("merged.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(orph, open("orphans.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
PY

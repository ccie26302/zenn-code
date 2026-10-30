#!/usr/bin/env python3
"""主要評価項目の集計(記事の数字の出どころ)"""
import json, collections, statistics as st
from pathlib import Path
D = Path(__file__).resolve().parent.parent / "data"
rows = [json.loads(l) for l in open(D / "e3_main.jsonl")]
redo = [json.loads(l) for l in open(D / "e3_owner_rfg_redo.jsonl")]
contaminated = {("owner", o) for o in ["r_gcs_rfg_list", "r_gcs_rfg_read", "r_gcs_rfg_write"]}
rows = [r for r in rows if (r["principal"], r["op"]) not in contaminated] + [r for r in redo if r["principal"] == "owner"]
res = collections.defaultdict(set)
for r in rows:
    res[(r["principal"], r["op"])].add("ok" if r["class"].startswith("success") else r["class"])
ops = sorted({r["op"] for r in rows})
print("== 主要1・2: 旧↔新で結果が食い違う操作(3回とも同じ結果のもの)")
for old, new in [("owner", "admin"), ("editor", "writer"), ("viewer", "reader")]:
    widen, narrow = [], []
    for o in ops:
        a, b = res[(old, o)], res[(new, o)]
        if len(a) != 1 or len(b) != 1: print("  unstable", old, new, o, a, b); continue
        a, b = next(iter(a)), next(iter(b))
        if a != b:
            (widen if b == "ok" else narrow).append(o)
    print(f"{old}->{new}: 広がる {len(widen)} {widen}\n            狭まる {len(narrow)} {narrow}")
n = len(rows); print("trials (after replacing contaminated):", n, collections.Counter(r["class"] for r in rows))
print("\n== testIamPermissions の一致(自分を除く)")
agree = collections.Counter(); tot = collections.Counter()
for r in rows:
    if r["principal"] == "me" or r["pred"] is None: continue
    tot[r["group"]] += 1; agree[r["group"]] += (r["pred"] == r["class"].startswith("success"))
for g in sorted(tot): print(f"  {g}: {agree[g]}/{tot[g]}")
print("\n== E5b+E5c 取り消しが効くまで(秒)")
vals = []
for l in open(D / "e5b.jsonl"):
    x = json.loads(l); vals.append(x["remove_effective_s"])
for l in open(D / "e5c.jsonl"):
    x = json.loads(l); vals.append(max(x["remove_pubsub"], x["remove_compute"]))
fast = [v for v in vals if v is not None and v < 2]; slow = [v for v in vals if v is not None and v >= 2]
print(f"  n={len(vals)} 2秒未満 {len(fast)} / 2秒以上 {len(slow)} (範囲 {min(slow):.1f}〜{max(slow):.1f}) / 15分で効かず {vals.count(None)}")
g = [json.loads(l)["grant_effective_s"] for l in open(D / "e5b.jsonl")] + [max(json.loads(l)["grant_pubsub"], json.loads(l)["grant_compute"]) for l in open(D / "e5c.jsonl")]
print(f"  付与: n={len(g)} 最大 {max(g):.2f} 秒")

#!/usr/bin/env python3
"""E6 の採点: 実測の正解(e6_truth.jsonl)と、洗い出しスクリプトの出力(e6_find_eval.json)を比べる"""
import json, collections, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import ROOT
TAG = sys.argv[1] if len(sys.argv) > 1 else "b"
truth = [json.loads(l) for l in open(ROOT / ("data/e6_truth.jsonl" if TAG == "b" else f"data/e6_truth_{TAG}.jsonl"))]
find = json.load(open(ROOT / ("data/e6_find_eval.json" if TAG == "b" else f"data/e6_find_eval_{TAG}.json")))
B = {(x["bucket"], x["pair"]): x for x in find["buckets"]}
D = {(x["dataset"], x["pair"]): x for x in find["datasets"]}
def tdir(r):
    o, n = r["old"], r["new"]
    if "unstable" in (o, n) or "undetermined" in (o, n): return None
    if o == n: return "none"
    return "widen" if n == "success" else "narrow"
def pdir(r):
    if r["kind"] == "dataset":
        x = D.get((r["resource"], r["pair"]), {"widen": [], "narrow": []})
        return "widen" if r["perm"] in x["widen"] else "narrow" if r["perm"] in x["narrow"] else "none"
    x = B[(r["resource"], r["pair"])]
    if r["perm"] == "storage.objects.get" and not x["ubla"]:
        if r["object"] in x["objects_widen_list"]: return "widen"
        if r["object"] in x["objects_narrow_list"]: return "narrow"
        return "none"
    return "widen" if r["perm"] in x["widen"] else "narrow" if r["perm"] in x["narrow"] else "none"
cm = collections.Counter(); excl = 0; bad = []
for r in truth:
    t = tdir(r)
    if t is None: excl += 1; continue
    p = pdir(r); cm[(t, p)] += 1
    if t != p: bad.append((r["resource"], r["object"], r["pair"], r["perm"], r["old"], r["new"], "pred=" + p))
print("units:", sum(cm.values()), "excluded(unstable/undetermined):", excl)
for k, v in sorted(cm.items()): print(" truth=%-6s pred=%-6s %d" % (k[0], k[1], v))
pos = sum(v for (t, p), v in cm.items() if t != "none")
miss = sum(v for (t, p), v in cm.items() if t != "none" and p != t)
fp = sum(v for (t, p), v in cm.items() if t == "none" and p != "none")
print(f"changed units (truth): {pos}  misses: {miss}  false positives: {fp} / {sum(v for (t,p),v in cm.items() if t=='none')} unchanged")
for b in bad: print("  ", b)

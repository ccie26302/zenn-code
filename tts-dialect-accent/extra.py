"""3回目の外部レビューを受けた追加の集計（探索的）。data/shape_measure.jsonl のキャッシュから計算し、API は呼ばない。"""
import os, json, math, collections, numpy as np
import corpus as C
HERE = os.path.dirname(os.path.abspath(__file__))
TOKYO_REG = {1: "low", 2: "low", 3: "low", 4: "high", 5: "high"}
rows = [json.loads(l) for l in open(os.path.join(HERE, "data", "shape_measure.jsonl"))]
rows = [q for q in rows if q.get("status") == "ok"]
for q in rows:
    q["register"] = "high" if q["shape"] == "atamadaka" else "low"
    q["label"] = "tokyo" if q["register"] == TOKYO_REG[q["cls"]] else "keihan"
def cond(st, lab, fr, stage=("gate", "main", "main_x")):
    return [q for q in rows if q["stage"] in stage and q["style"] == st and q["frame"] == fr and q["voice"] in C.VOICES[lab]]
def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),) * 2
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d
pct = lambda x: "%5.1f%%" % (100 * x)
K = cond("K", "osaka", "kansai"); N = cond("N", "osaka", "kansai"); T = cond("T", "osaka", "kansai")
TK = cond("K", "tokyo", "kansai"); TN = cond("N", "tokyo", "kansai"); G = cond("N", "tokyo", "standard")

print("## 類ごとの形の内訳（平板＝低高高、尾高＝低高低、頭高＝高低低）")
for name, s in (("東京×指示なし×標準（ゲート）", G), ("大阪×関西の指示", K), ("大阪×指示なし", N), ("大阪×東京の指示", T), ("東京×指示なし×関西の枠", TN)):
    print(" ", name)
    for c in (1, 2, 3, 4, 5):
        cc = collections.Counter(q["shape"] for q in s if q["cls"] == c)
        print(f"     {c}類 平板 {cc['heiban']:2d} 尾高 {cc['odaka']:2d} 頭高 {cc['atamadaka']:2d}")

print("\n## 感度分析：判定があいまいな発話を除く（最大相関<0.5、または高起と低起の最良の相関の差<0.2）")
def confident(q):
    hi = q["r_atama"]; lo = max(q["r_heiban"], q["r_odaka"])
    return max(hi, lo) >= 0.5 and abs(hi - lo) >= 0.2
for name, s in (("ゲート", G), ("大阪×関西の指示", K), ("大阪×指示なし", N), ("大阪×東京の指示", T), ("東京×関西の指示", TK), ("東京×指示なし×関西の枠", TN)):
    a = [q for q in s if q["cls"] > 1]; b = [q for q in a if confident(q)]
    ka = np.mean([q["label"] == "keihan" for q in a]); kb = np.mean([q["label"] == "keihan" for q in b]) if b else float("nan")
    print(f"  {name:22s} 全体 京阪式 {pct(ka)} (n={len(a)})  → 確信のある発話だけ {pct(kb)} (n={len(b)}, 除外 {pct(1-len(b)/len(a))})")

print("\n## 再現性（大阪2声×関西の指示、同じ原稿2回）")
rep = [q for q in rows if q["stage"] == "repeat"]
for scope, cls in (("全24語", (1, 2, 3, 4, 5)), ("2〜5類", (2, 3, 4, 5))):
    n = d = d3 = 0
    for q in rep:
        if q["cls"] not in cls: continue
        o = [p for p in K if p["voice"] == q["voice"] and p["word"] == q["word"]]
        if not o: continue
        n += 1; d += o[0]["label"] != q["label"]; d3 += o[0]["shape"] != q["shape"]
    lo, hi = wilson(d, n); print(f"  {scope}: 型（東京式/京阪式）の食い違い {d}/{n} = {pct(d/n)} [95%区間 {pct(lo)}, {pct(hi)}]  3つの形の食い違い {d3}/{n}")

print("\n## 京阪の正解の根拠別（大阪×関西の指示、2〜5類）")
for src in ("確認", "類"):
    s = [q for q in K if q["cls"] > 1 and q["keihan_src"] == src]
    print(f"  {src}: 京阪式 {sum(q['label']=='keihan' for q in s)}/{len(s)} = {pct(np.mean([q['label']=='keihan' for q in s]))}")

print("\n## 文の位置（大阪×関西の指示、2〜5類）")
a = [q for q in K if q["cls"] > 1]
f = [q["label"] == "keihan" for q in a if q["pos"] <= 12]; b = [q["label"] == "keihan" for q in a if q["pos"] > 12]
from scipy.stats import fisher_exact
t = [[sum(f), len(f) - sum(f)], [sum(b), len(b) - sum(b)]]
print(f"  前半12文 {pct(np.mean(f))} (n={len(f)})  後半12文 {pct(np.mean(b))} (n={len(b)})  Fisher p={fisher_exact(t)[1]:.3f}")

print("\n## 関西の指示と指示なし（大阪6声、同じ声・同じ語で対にする、2〜5類）")
key = lambda q: (q["voice"], q["word"])
dk = {key(q): q["label"] for q in K if q["cls"] > 1}; dn = {key(q): q["label"] for q in N if q["cls"] > 1}
b01 = sum(1 for k in dk if k in dn and dk[k] == "keihan" and dn[k] == "tokyo"); b10 = sum(1 for k in dk if k in dn and dk[k] == "tokyo" and dn[k] == "keihan")
nn = b01 + b10; p = min(1, 2 * sum(math.comb(nn, i) for i in range(0, min(b01, b10) + 1)) / 2 ** nn)
print(f"  関西の指示でだけ京阪式 {b01} / 指示なしでだけ京阪式 {b10}  McNemar p={p:.3f}（声のまとまりを無視した参考値）")

print("\n## 東京の声×関西の指示：声ごとの4・5類の低起")
for v in C.VOICES["tokyo"]:
    s = [q for q in TK if q["voice"] == v and q["cls"] in (4, 5)]
    print(f"  {v}: {sum(q['register']=='low' for q in s)}/{len(s)}")

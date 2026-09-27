"""14節（探索）：Cloud Text-to-Speech の Gemini-TTS 3.1 Flash preview、6声×3条件×2回。data/shape_measure.jsonl から集計。"""
import os, json, math, collections, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
TOKYO_REG = {1: "low", 2: "low", 3: "low", 4: "high", 5: "high"}
rows = [json.loads(l) for l in open(os.path.join(HERE, "data", "shape_measure.jsonl"))]
meta = {json.loads(l)["req"]: json.loads(l) for l in open(os.path.join(HERE, "data", "vertex31.jsonl"))}
rows = [q for q in rows if q.get("stage") == "vertex31x"]
print("発話", len(rows), "状態", dict(collections.Counter(q.get("status") for q in rows)))
rows = [q for q in rows if q.get("status") == "ok"]
for q in rows:
    q["register"] = "high" if q["shape"] == "atamadaka" else "low"
    q["label"] = "tokyo" if q["register"] == TOKYO_REG[q["cls"]] else "keihan"; q["rep"] = meta[q["req"]]["rep"]
def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return (c - h) / d, (c + h) / d
pct = lambda x: "%5.1f%%" % (100 * x)
print("\n## 条件ごと（6声×2回）")
for st, fr, name in (("N", "standard", "指示なし×標準の文"), ("N", "kansai", "指示なし×関西の文"), ("K", "kansai", "関西の指示×関西の文")):
    s = [q for q in rows if q["style"] == st and q["frame"] == fr]
    a = [q for q in s if q["cls"] > 1]; k = sum(q["label"] == "keihan" for q in a)
    low45 = [q for q in s if q["cls"] in (4, 5)]; hi23 = [q for q in s if q["cls"] in (2, 3)]
    lo, hi = wilson(k, len(a))
    print(f"  {name:12s} 京阪式 {pct(k/len(a))} [{pct(lo)}, {pct(hi)}] ({k}/{len(a)})  東京式 {pct(1-k/len(a))}"
          f"  4・5類の低起 {sum(q['register']=='low' for q in low45)}/{len(low45)}  2・3類の高起 {sum(q['register']=='high' for q in hi23)}/{len(hi23)}")
    per = {v: np.mean([q["label"] == "keihan" for q in a if q["voice"] == v]) for v in sorted({q["voice"] for q in a})}
    print("     声ごとの京阪式:", {v: round(100 * x) for v, x in per.items()})
print("\n## E1 標準の文で東京式80%以上か")
s = [q for q in rows if q["frame"] == "standard" and q["cls"] > 1]; t = np.mean([q["label"] == "tokyo" for q in s])
print(f"  東京式 {pct(t)} → {'支持' if t >= .8 else '外れ（3.1 は記述にとどめる）'}")
print("\n## E2 4・5類の低起：指示なし×関西 vs 関西の指示×関西")
f = lambda st: [q for q in rows if q["style"] == st and q["frame"] == "kansai" and q["cls"] in (4, 5)]
a, b = f("N"), f("K"); ra = np.mean([q["register"] == "low" for q in a]); rb = np.mean([q["register"] == "low" for q in b])
print(f"  指示なし {pct(ra)} / 関西の指示 {pct(rb)} → {'支持' if ra > rb else '外れ'}")
print("\n## E3 再現性（同じ原稿2回で型の判定が食い違う割合、2〜5類）")
d = collections.defaultdict(dict)
for q in rows:
    if q["cls"] > 1: d[(q["voice"], q["style"], q["frame"], q["word"])][q["rep"]] = q["label"]
pairs = [v for v in d.values() if len(v) == 2]; diff = sum(v[1] != v[2] for v in pairs); lo, hi = wilson(diff, len(pairs))
print(f"  {diff}/{len(pairs)} = {pct(diff/len(pairs))} [{pct(lo)}, {pct(hi)}]")

print("\n## 追加：指示なし vs 関西の指示（関西の文）")
from scipy.stats import fisher_exact, t as tdist, wilcoxon
kk = {(q["voice"], q["word"], q["rep"]): q["label"] for q in rows if q["style"] == "K" and q["frame"] == "kansai" and q["cls"] > 1}
nn = {(q["voice"], q["word"], q["rep"]): q["label"] for q in rows if q["style"] == "N" and q["frame"] == "kansai" and q["cls"] > 1}
b01 = sum(1 for k in nn if k in kk and nn[k] == "keihan" and kk[k] == "tokyo"); b10 = sum(1 for k in nn if k in kk and nn[k] == "tokyo" and kk[k] == "keihan")
n = b01 + b10; p = min(1, 2 * sum(math.comb(n, i) for i in range(0, min(b01, b10) + 1)) / 2 ** n)
print(f"  McNemar：指示なしでだけ京阪式 {b01} / 指示ありでだけ {b10}  p={p:.3f}")
a = [q["register"] == "low" for q in rows if q["style"] == "N" and q["frame"] == "kansai" and q["cls"] in (4, 5)]
b = [q["register"] == "low" for q in rows if q["style"] == "K" and q["frame"] == "kansai" and q["cls"] in (4, 5)]
print(f"  E2 Fisher p={fisher_exact([[sum(a), len(a)-sum(a)], [sum(b), len(b)-sum(b)]])[1]:.3f}")
for st in ("N", "K"):
    per = [np.mean([q["label"] == "keihan" for q in rows if q["style"] == st and q["frame"] == "kansai" and q["cls"] > 1 and q["voice"] == v]) for v in sorted({q["voice"] for q in rows})]
    m, se = np.mean(per), np.std(per, ddof=1) / np.sqrt(len(per)); h = tdist.ppf(.975, len(per) - 1) * se
    print(f"  {st} 声単位の平均 {pct(m)} [声単位 t 区間 {pct(m-h)}, {pct(m+h)}]")
print("  標準語の文で 4・5類が低起と誤判定された割合（雑音の下限）:", sum(q["register"] == "low" for q in rows if q["frame"] == "standard" and q["cls"] in (4, 5)), "/", sum(1 for q in rows if q["frame"] == "standard" and q["cls"] in (4, 5)))

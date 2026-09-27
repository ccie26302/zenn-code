"""Q2 の集計（記事の結果5）。q2.py の出力 data/q2_wa.csv と、聴き分けの回答から。"""
import os, csv, json, math, collections, numpy as np
from scipy.stats import wilcoxon
HERE = os.path.dirname(os.path.abspath(__file__))
R = [r for r in csv.DictReader(open(os.path.join(HERE, "data", "q2_wa.csv"))) if r["status"] == "ok"]
def agg(style, key):
    d = collections.defaultdict(list)
    for r in R:
        if r["style"] == style: d[int(r["sent"])].append(float(r[key]))
    return {k: np.mean(v) for k, v in d.items()}
for key, name in (("diff", "「わ」−直前の拍（半音）"), ("slope", "「わ」の中の傾き（半音/秒）"), ("wa_ms", "「わ」の長さ（ms）")):
    O, K, N = agg("OJ", key), agg("KF", key), agg("N", key); s = sorted(set(O) & set(K))
    print(f"{name}: お嬢様 {np.mean(list(O.values())):.2f} / 関西 {np.mean(list(K.values())):.2f} / 指示なし {np.mean(list(N.values())):.2f}"
          f"  お嬢様>関西 {sum(O[i] > K[i] for i in s)}/{len(s)}  符号付き順位検定 p={wilcoxon([O[i] for i in s], [K[i] for i in s]).pvalue:.4f}")
print("判定不能:", collections.Counter(r["req"] for r in csv.DictReader(open(os.path.join(HERE, "data", "q2_wa.csv"))) if r["status"] != "ok"))
K = json.load(open(os.path.join(HERE, "data", "listening_key.json"))); A = json.load(open(os.path.join(HERE, "data", "listening_answers.json")))
a = [k for k in K if k[0] == "a"]; ok = sum(A[k] == K[k]["answer"] for k in a)
print(f"聴き分け: {ok}/{len(a)} 正解  片側二項検定 p={sum(math.comb(len(a), i) for i in range(ok, len(a) + 1)) / 2 ** len(a):.2e}")

"""集計。事前登録(PLAN.md v2)に沿って出す。

主指標: 自動化率@誤り2%(1%/5%併記)、対数損失
クラスタブートストラップ: 属性の組(用途区分・金額・領収書・承認)単位で 10,000回
エラー: 誤答・一様確率として数える
"""
import json, os, sys, math, collections, random
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
L = ["A","B","C","D"]; EPS = 1e-6
C = json.load(open(os.path.join(HERE,"data","corpus.json")))
ROW = {r["id"]: r for r in C["rows"]}
RNG = np.random.default_rng(20260923)
NB = int(os.environ.get("NBOOT", 10000))

def load(name):
    p = os.path.join(HERE,"data",name)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []

def cluster(r):
    x = ROW[r["id"]]
    return (x["kind"], x["amount"], x["receipt"], x["mgr"])

def norm(rec):
    """1試行を (正誤, 確信度, 分布) に。エラーは誤答・一様。"""
    if rec.get("err"):
        return 0, 0.25, {k:.25 for k in L}
    if rec.get("probs"):
        p = rec["probs"]; pred = max(p, key=p.get)
        return int(pred == rec["label"]), p[pred], p
    conf = rec.get("conf", 0.25)                       # 言語化(予測ラベルの確信度のみ)
    return int(rec.get("pred") == rec["label"]), conf, None

def logloss(dist, y):
    return -math.log(max(EPS, min(1-EPS, dist.get(y, 0.0))))

def brier(dist, y):
    return sum((dist.get(k,0)-(1.0 if k==y else 0.0))**2 for k in L)

def ece(conf, corr, bins=10, equal_mass=False):
    conf = np.asarray(conf); corr = np.asarray(corr); n = len(conf)
    if equal_mass:
        order = np.argsort(conf); edges = np.array_split(order, bins)
        return sum(len(g)/n*abs(corr[g].mean()-conf[g].mean()) for g in edges if len(g))
    e = 0.0
    for i in range(bins):
        lo, hi = i/bins, (i+1)/bins
        m = (conf > lo) & (conf <= hi) if i else (conf >= lo) & (conf <= hi)
        if m.sum(): e += m.sum()/n * abs(corr[m].mean() - conf[m].mean())
    return e

def automation(conf, corr, max_err):
    """確信度の高い順に採用。同じ確信度はまとめて採否を決める(途中で切れない)。"""
    conf = np.asarray(conf); corr = np.asarray(corr); n = len(conf)
    best = 0.0
    for t in sorted(set(conf.tolist()), reverse=True):
        m = conf >= t
        err = 1 - corr[m].mean()
        if err <= max_err + 1e-12: best = max(best, m.sum()/n)
    return best

def metrics(recs):
    rows = [(norm(r), r) for r in recs]
    corr = [x[0][0] for x in rows]; conf = [x[0][1] for x in rows]
    dists = [(x[0][2], x[1]["label"]) for x in rows]
    out = dict(n=len(rows), acc=float(np.mean(corr)),
               ece10=ece(conf, corr), ece_mass=ece(conf, corr, equal_mass=True),
               auto1=automation(conf, corr, .01), auto2=automation(conf, corr, .02),
               auto5=automation(conf, corr, .05),
               conf_mean=float(np.mean(conf)), conf100=float(np.mean([c >= .9999 for c in conf])))
    if all(d is not None for d, _ in dists):
        out["logloss"] = float(np.mean([logloss(d, y) for d, y in dists]))
        out["brier"] = float(np.mean([brier(d, y) for d, y in dists]))
    return out

def boot(recs, fn, nb=NB):
    groups = collections.defaultdict(list)
    for r in recs: groups[cluster(r)].append(r)
    keys = list(groups); vals = []
    for _ in range(nb):
        pick = RNG.integers(0, len(keys), len(keys))
        s = [r for i in pick for r in groups[keys[i]]]
        vals.append(fn(s))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))

def test_of(recs, cond):
    return [r for r in recs if r["cond"] == cond and r["split"] == "test"]

def mcnemar(a, b):
    """同じ項目で a と b の正誤を突き合わせる正確検定(両側)"""
    da = {r["id"]: norm(r)[0] for r in a}; db = {r["id"]: norm(r)[0] for r in b}
    ids = set(da) & set(db)
    n01 = sum(1 for i in ids if da[i] == 0 and db[i] == 1)
    n10 = sum(1 for i in ids if da[i] == 1 and db[i] == 0)
    n = n01 + n10
    if n == 0: return n01, n10, 1.0
    k = min(n01, n10)
    p = sum(math.comb(n, i) for i in range(0, k+1)) / 2**n * 2
    return n01, n10, min(1.0, p)

# ---------- 事後校正: 温度スケーリング(学習データで当てはめ) ----------
def temp_fit(train_recs):
    def nll(T):
        s = 0.0
        for r in train_recs:
            if r.get("err") or not r.get("probs"): continue
            lg = {k: math.log(max(EPS, r["probs"][k]))/T for k in L}
            m = max(lg.values()); z = sum(math.exp(v-m) for v in lg.values())
            s -= (lg[r["label"]] - m - math.log(z))
        return s
    grid = [0.25,0.35,0.5,0.7,1.0,1.4,2,2.8,4,5.6,8,11,16]
    return min(grid, key=nll)

def temp_apply(recs, T):
    out = []
    for r in recs:
        r = dict(r)
        if r.get("probs") and not r.get("err"):
            lg = {k: math.log(max(EPS, r["probs"][k]))/T for k in L}
            m = max(lg.values()); z = sum(math.exp(v-m) for v in lg.values())
            r["probs"] = {k: math.exp(lg[k]-m)/z for k in L}
        out.append(r)
    return out

def pct(x): return "%5.1f%%" % (100*x)

def main():
    acc = load("acc.jsonl")
    if not acc: sys.exit("acc.jsonl がありません")
    conds = ["A1","A2","B1","B2","C1t","C1d","C2t","C2d"]
    sc = json.load(open(os.path.join(HERE,"data","shortcut.json")))["shortcut_acc"]
    res = {}
    print("総試行 %d / エラー %d" % (len(acc), sum(1 for r in acc if r.get("err"))))
    print("エラー内訳:", dict(collections.Counter((r["cond"], r["err"][:40]) for r in acc if r.get("err"))) or "なし")
    print("\n近道(金額を読まない)の下限: %s\n" % pct(sc))
    print("%-4s %4s %7s %7s %7s %7s %7s %7s %7s %7s" % ("条件","n","正答","金額層","自動@1","自動@2","自動@5","対数損","ECE","確信100"))
    for c in conds:
        t = test_of(acc, c)
        if not t: continue
        m = metrics(t)
        m["acc_amount"] = metrics([r for r in t if r["reason"]=="amount_decides"])["acc"]
        res[c] = m
        print("%-4s %4d %7s %7s %7s %7s %7s %7s %7.3f %7s" % (c, m["n"], pct(m["acc"]), pct(m["acc_amount"]),
              pct(m["auto1"]), pct(m["auto2"]), pct(m["auto5"]),
              ("%.3f" % m["logloss"]) if "logloss" in m else "  -", m["ece10"], pct(m["conf100"])))
    # ---- 文体別 ----
    print("\n文体別の正答率")
    for c in conds:
        t = test_of(acc, c)
        if not t: continue
        print("  %-4s " % c + "  ".join("%s %s" % (s, pct(metrics([r for r in t if r["style"]==s])["acc"]))
                                    for s in ("explicit","narrative","indirect")))
    # ---- 主比較とCI ----
    print("\n主比較(クラスタブートストラップ %d回)" % NB)
    for c in ("A1","C2t","B1"):
        t = test_of(acc, c)
        lo, hi = boot(t, lambda s: metrics(s)["auto2"])
        a_lo, a_hi = boot([r for r in t if r["reason"]=="amount_decides"], lambda s: metrics(s)["acc"])
        res[c]["auto2_ci"] = (lo, hi); res[c]["acc_amount_ci"] = (a_lo, a_hi)
        print("  %-4s 自動化@2%% %s [%s, %s]   金額層の正答率 %s [%s, %s]" % (
              c, pct(res[c]["auto2"]), pct(lo), pct(hi), pct(res[c]["acc_amount"]), pct(a_lo), pct(a_hi)))
    n01, n10, p = mcnemar(test_of(acc,"A1"), test_of(acc,"C2t"))
    print("  A1 vs C2t 正誤の食い違い: A1誤C2t正 %d / A1正C2t誤 %d  McNemar p=%.4f" % (n01, n10, p))
    am = lambda c: [r for r in test_of(acc,c) if r["reason"]=="amount_decides"]
    n01, n10, p = mcnemar(am("A1"), am("B1"))
    print("  A1 vs B1(金額層) 食い違い: A1誤B1正 %d / A1正B1誤 %d  McNemar p=%.4f" % (n01, n10, p))
    # ---- 事後校正 ----
    print("\n事後校正(学習200件で温度スケーリング → テストで評価)")
    for c in ("A1","A2","C1d","C2d"):
        tr = [r for r in acc if r["cond"]==c and r["split"]=="train"]
        te = test_of(acc, c)
        if not tr or not te: continue
        T = temp_fit(tr); m0 = metrics(te); m1 = metrics(temp_apply(te, T))
        res[c]["T"] = T; res[c]["cal"] = m1
        print("  %-4s T=%-5s 対数損失 %.3f→%.3f  ECE %.3f→%.3f  自動化@2%% %s→%s" % (
              c, T, m0.get("logloss",float('nan')), m1.get("logloss",float('nan')),
              m0["ece10"], m1["ece10"], pct(m0["auto2"]), pct(m1["auto2"])))
    json.dump(res, open(os.path.join(HERE,"data","summary_acc.json"),"w"), ensure_ascii=False, indent=1, default=str)
    return res

if __name__ == "__main__":
    main()

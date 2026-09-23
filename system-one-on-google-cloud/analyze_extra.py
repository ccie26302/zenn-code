"""速度・規程変更・再現性・長い規程・カスケードの集計。"""
import json, os, sys, math, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A

def q(v, p): return float(np.percentile(v, p)) if len(v) else float("nan")

def latency():
    lat = A.load("lat.jsonl")
    if not lat: print("lat なし"); return {}
    ok = [r for r in lat if not r["warmup"] and not r.get("err")]
    print("速度(日本から・逐次・ウォームアップ除外) 総%d / エラー%d" % (len(lat), sum(1 for r in lat if r.get("err"))))
    fl = q([r["ms"] for r in ok if r["cond"]=="FLOOR"], 50)
    out = {}
    print("  %-6s %4s %7s %7s %7s %9s" % ("条件","n","p50","p90","p99","p50-下限"))
    for c in ["FLOOR","B1","B2","A2","A1","C2t","C2d","C1t","C1d"]:
        v = [r["ms"] for r in ok if r["cond"]==c]
        if not v: continue
        out[c] = dict(n=len(v), p50=q(v,50), p90=q(v,90), p99=q(v,99))
        print("  %-6s %4d %6.0fms %6.0fms %6.0fms %8.0fms" % (c, len(v), q(v,50), q(v,90), q(v,99),
              q(v,50)-fl if c!="FLOOR" else 0))
    # 埋め込みの内訳
    for c in ("B1","B2"):
        e = [r["ms_embed"] for r in ok if r["cond"]==c]; k = [r["ms_clf"] for r in ok if r["cond"]==c]
        if e: print("  %s 内訳: 埋め込み p50 %.0fms / 分類器 p50 %.3fms" % (c, q(e,50), q(k,50)))
    # 二峰性の確認
    for c in ("B1","B2","A1"):
        v = sorted(r["ms"] for r in ok if r["cond"]==c)
        if v: print("  %s 分布の十分位: %s" % (c, [round(q(v,p)) for p in (10,30,50,70,90)]))
    return out

def policy():
    pol = A.load("policy.jsonl"); acc = A.load("acc.jsonl")
    if not pol: print("policy なし"); return {}
    print("\n規程変更(5万→3万)。生成系はプロンプト差し替えのみ、B は再学習なし")
    out = {}
    for c in ("A1","A2","C1t","C2t"):
        for flip in (1, 0):
            s = [r for r in pol if r["cond"]==c and r["flip"]==flip]
            if not s: continue
            a = np.mean([0 if r.get("err") else int(r.get("pred")==r["label_th30"]) for r in s])
            out[(c,flip)] = a
            print("  %-4s %s  n=%2d  新規程での正答 %s" % (c, "反転する項目" if flip else "反転しない対照", len(s), A.pct(a)))
    for c in ("B1","B2"):
        t = A.test_of(acc, c)
        s = [r for r in t if r["label"] != r["label_th30"]]
        a = np.mean([0 if r.get("err") else int(r.get("pred")==r["label_th30"]) for r in s])
        out[(c,1)] = a
        print("  %-4s 反転する項目  n=%2d  新規程での正答 %s  (旧規程のまま判定するため)" % (c, len(s), A.pct(a)))
    # --- 生の正答率は水増しされる。旧規程で正しかった項目が新規程で切り替わったかで測る ---
    ret = {(r["cond"],r["id"]):r for r in A.load("acc_retry.jsonl") if not r.get("err")}
    old = {}
    for r in acc:
        if r["split"] != "test": continue
        rr = ret.get((r["cond"],r["id"]), r) if r.get("err") else r
        old[(r["cond"],r["id"])] = rr.get("pred")
    print("  --- 本当の追従率: 旧規程で A と正しく判定した項目のうち、新規程で B に切り替えた割合 ---")
    for c in ("A1","A2","C1t","C2t"):
        s = [r for r in pol if r["cond"]==c and r["flip"]==1 and not r.get("err")]
        knew = [r for r in s if old.get((c,r["id"]))=="A"]
        sw = sum(1 for r in knew if r["pred"]=="B")
        out[(c,"follow")] = (sw, len(knew), len(s))
        print("  %-4s 切り替えた %2d / 旧規程で理解していた %2d (反転項目 %d件中)" % (c, sw, len(knew), len(s)))
    return out

def repeat():
    rep = A.load("repeat.jsonl")
    if not rep: print("repeat なし"); return {}
    print("\n再現性(同一入力を5回。temperature=0・seed固定)")
    out = {}
    for c in ("A1","A2"):
        g = collections.defaultdict(list)
        for r in rep:
            if r["cond"]==c and not r.get("err"): g[r["id"]].append(r)
        flip = sum(1 for v in g.values() if len({x["pred"] for x in v}) > 1)
        spread = [max(max(x["probs"].values()) for x in v) - min(max(x["probs"].values()) for x in v) for v in g.values()]
        out[c] = dict(items=len(g), flip=flip, spread_max=max(spread), spread_med=q(spread,50))
        print("  %-3s 項目%d  判定が食い違った項目 %d  最大確率の振れ幅 中央%.4f / 最大%.4f" % (
              c, len(g), flip, q(spread,50), max(spread)))
        for iid, v in g.items():
            if len({x["pred"] for x in v}) > 1:
                print("       例 %s 正解%s  %s" % (iid, v[0]["label"], [(x["pred"], round(max(x["probs"].values()),3)) for x in v]))
    return out

def long():
    lo = A.load("long.jsonl"); la = A.load("lat.jsonl")
    if not lo: print("long なし"); return {}
    print("\n長い規程(約3,000トークン)での速度")
    out = {}
    for c in ("FLOOR","B1","A1","C1t"):
        s = [r["ms"] for r in lo if r["cond"]==c and not r["warmup"] and not r.get("err")]
        b = [r["ms"] for r in la if r["cond"]==c and not r["warmup"] and not r.get("err")]
        if s:
            out[c] = (q(b,50), q(s,50))
            print("  %-6s 短い規程 p50 %6.0fms → 長い規程 p50 %6.0fms  差 %+5.0fms" % (c, q(b,50), q(s,50), q(s,50)-q(b,50)))
    return out

def cascade():
    acc = A.load("acc.jsonl")
    print("\nカスケード(1段目で確信度が τ 未満なら2段目へ回す)")
    tests = {c: {r["id"]: r for r in A.test_of(acc, c)} for c in ("B1","A2","A1","C1t")}
    for first, second in (("B1","C1t"), ("A2","C1t"), ("A1","C1t")):
        f, s = tests[first], tests[second]
        ids = list(set(f) & set(s))
        print("  %s → %s" % (first, second))
        for tau in (0.5, 0.7, 0.8, 0.9, 0.95, 0.99):
            corr = []; esc = 0
            for i in ids:
                c1, p1, _ = A.norm(f[i])
                if p1 >= tau: corr.append(c1)
                else: esc += 1; corr.append(A.norm(s[i])[0])
            print("     τ=%.2f  2段目へ %5.1f%%  全体の正答 %s" % (tau, 100*esc/len(ids), A.pct(np.mean(corr))))

if __name__ == "__main__":
    what = sys.argv[1:] or ["latency","policy","repeat","long","cascade"]
    for w in what: globals()[w]()

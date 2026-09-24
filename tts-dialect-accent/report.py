"""本測定の集計（PLAN.md 6節・12節）。記事の表はすべてここから出す。

使い方: PROJECT_ID=... GCS_BUCKET=... python report.py
"""
import os, json, csv, collections, numpy as np
import acoustic as A, corpus as C, analyze as Z, shape as S, stt
HERE = os.path.dirname(os.path.abspath(__file__))
T = {k: np.array(v) for k, v in json.load(open(os.path.join(HERE, "data", "templates_gate.json"))).items()}
TOKYO_REG = {1: "low", 2: "low", 3: "low", 4: "high", 5: "high"}
CACHE = os.path.join(HERE, "data", "shape_measure.jsonl")
RNG = np.random.default_rng(20260925)

def measure_all(stages=("gate", "main", "main_x", "repeat", "vertex31")):
    done = {}
    if os.path.exists(CACHE):
        for l in open(CACHE):
            q = json.loads(l); done.setdefault(q["req"], []).append(q)
    rows = []
    for r in Z.requests():
        if r["stage"] not in stages: continue
        if r["req"] not in done:
            wav = Z.fetch(r); x, sr = A.load(wav)
            segs, th = Z.segments(x, sr, 26)
            out = []
            if segs is None: out.append(dict(req=r["req"], status="split_failed"))
            else:
                rng = A.voice_range(x, sr)
                for i, (a, b) in enumerate(segs[1:-1]):
                    w = r["words"][i]; cls, morae, src = C.WORDS[w]
                    base = dict(req=r["req"], stage=r["stage"], voice=r["voice"], style=r["style"], frame=r["frame"],
                                pos=i + 1, word=w, cls=cls, keihan_src=src)
                    try:
                        v, st = S.vector(x[int(a * sr):int(b * sr)], sr, morae + C.FRAMES[r["frame"]][1], rng)
                    except Exception as e:
                        out.append(dict(base, status="align_failed")); continue
                    if v is None: out.append(dict(base, status=st)); continue
                    best, sc = S.nearest(v, T)
                    out.append(dict(base, status="ok", shape=best, r_heiban=sc["heiban"], r_odaka=sc["odaka"], r_atama=sc["atamadaka"], vec=list(map(float, v))))
                # 書き起こし（Q3）
                cache = os.path.join(HERE, "data", "stt", f"req{r['req']:03d}.json")
                if not os.path.exists(cache):
                    os.makedirs(os.path.dirname(cache), exist_ok=True); json.dump(stt.transcribe(wav), open(cache, "w"), ensure_ascii=False)
            with open(CACHE, "a") as f:
                for q in out: f.write(json.dumps(q, ensure_ascii=False) + "\n")
            done[r["req"]] = out
        rows += done[r["req"]]
    for q in rows:
        if q.get("status") == "ok":
            reg = "high" if q["shape"] == "atamadaka" else "low"
            q["register"] = reg
            q["label"] = "tokyo" if reg == TOKYO_REG[q["cls"]] else ("keihan" if q["cls"] > 1 else "not_tokyo")
        else: q["label"] = q.get("status")
    return rows

def rate(rows, lab, classes=(2, 3, 4, 5)):
    s = [q for q in rows if q["cls"] in classes and q["label"] in ("tokyo", "keihan")]
    return (np.mean([q["label"] == lab for q in s]) if s else np.nan), len(s)

def boot_voice_word(rows, lab, nb=10000):
    """声→語の2段ブートストラップ"""
    s = [q for q in rows if q["cls"] > 1 and q["label"] in ("tokyo", "keihan")]
    byv = collections.defaultdict(lambda: collections.defaultdict(list))
    for q in s: byv[q["voice"]][q["word"]].append(q["label"] == lab)
    vs = list(byv); vals = []
    for _ in range(nb):
        acc = []
        for v in RNG.choice(vs, len(vs)):
            ws = list(byv[v])
            for w in RNG.choice(ws, len(ws)): acc += byv[v][w]
        vals.append(np.mean(acc))
    return np.percentile(vals, 2.5), np.percentile(vals, 97.5)

def boot_word(rows, lab, nb=10000):
    byw = collections.defaultdict(list)
    for q in rows:
        if q["cls"] > 1 and q["label"] in ("tokyo", "keihan"): byw[q["word"]].append(q["label"] == lab)
    ws = list(byw); vals = [np.mean(sum((byw[w] for w in RNG.choice(ws, len(ws))), [])) for _ in range(nb)]
    return np.percentile(vals, 2.5), np.percentile(vals, 97.5)

def pct(x): return "%5.1f%%" % (100 * x)

def main():
    rows = measure_all()
    keys = ["req","stage","voice","style","frame","pos","word","cls","keihan_src","status","shape","register","label","r_heiban","r_odaka","r_atama"]
    with open(os.path.join(HERE, "data", "utterances_shape.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, keys, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print("発話の状態:", dict(collections.Counter(q["label"] for q in rows)))
    cond = lambda st, lab, fr: [q for q in rows if q["stage"] in ("gate", "main", "main_x") and q["style"] == st and q["frame"] == fr and q["voice"] in C.VOICES[lab]]
    print("\n## 条件ごと（2〜5類、判定できた発話）")
    for name, st, lab, fr in [("東京×指示なし×標準（ゲート）", "N", "tokyo", "standard"), ("大阪×関西の指示", "K", "osaka", "kansai"),
                              ("大阪×指示なし", "N", "osaka", "kansai"), ("大阪×東京の指示", "T", "osaka", "kansai"), ("東京×関西の指示", "K", "tokyo", "kansai"),
                              ("東京×指示なし×関西の枠（探索）", "N", "tokyo", "kansai")]:
        s = cond(st, lab, fr); tk, n = rate(s, "tokyo"); kh, _ = rate(s, "keihan")
        un = sum(1 for q in s if q["label"] not in ("tokyo", "keihan", "not_tokyo"))
        b = boot_voice_word(s, "keihan") if n else (np.nan, np.nan)
        print(f"  {name:22s} 京阪式 {pct(kh)} [{pct(b[0])}, {pct(b[1])}]  東京式 {pct(tk)}  n={n}  判定不能 {un}")
        for c in (1, 2, 3, 4, 5):
            ss = [q for q in s if q["cls"] == c and q["label"] in ("tokyo", "keihan", "not_tokyo")]
            if ss: print(f"      {c}類 東京式 {sum(q['label']=='tokyo' for q in ss)}/{len(ss)}")
    print("\n## 参考：Gemini-TTS 3.1 Flash preview（Cloud Text-to-Speech）")
    for v in ("Kore", "Charon"):
        for st in ("K", "N"):
            s = [q for q in rows if q["stage"] == "vertex31" and q["voice"] == v and q["style"] == st]
            kh, n = rate(s, "keihan"); print(f"  {v:7s} {st} 京阪式 {pct(kh)} 東京式 {pct(rate(s,'tokyo')[0])} n={n}")
    print("\n## 大阪の声ごと（関西の指示）")
    for v in C.VOICES["osaka"]:
        s = [q for q in cond("K", "osaka", "kansai") if q["voice"] == v]
        kh, n = rate(s, "keihan"); lo, hi = boot_word(s, "keihan")
        print(f"  {v:22s} 京阪式 {pct(kh)} [{pct(lo)}, {pct(hi)}] n={n}")
    # 予測
    K = cond("K", "osaka", "kansai"); Nn = cond("N", "osaka", "kansai"); Tt = cond("T", "osaka", "kansai"); TK = cond("K", "tokyo", "kansai")
    per = [rate([q for q in K if q["voice"] == v], "keihan")[0] for v in C.VOICES["osaka"]]
    if any(p != p for p in per): print("\n（本測定が揃っていないので予測の判定は保留）"); return rows
    print("\n## 事前予測")
    print("  P2 京阪式<70% の声: %d/6 → %s" % (sum(p < .7 for p in per), "支持" if sum(p < .7 for p in per) >= 5 else "外れ"))
    lo, hi = boot_voice_word(K, "tokyo"); print("  P3 エセ率 %s [%s, %s] → %s" % (pct(rate(K, "tokyo")[0]), pct(lo), pct(hi), "支持" if lo >= .2 else "外れ"))
    print("  P5 大阪×K %s vs 東京×K %s" % (pct(rate(K, "keihan")[0]), pct(rate(TK, "keihan")[0])))
    d6 = rate(Tt, "tokyo")[0] - rate(K, "tokyo")[0]; print("  P6 東京式 T−K = %+.1fpt → %s" % (100 * d6, "支持" if d6 >= .2 else "外れ"))
    d6b = abs(rate(Nn, "keihan")[0] - rate(K, "keihan")[0]); print("  P6' |N−K| 京阪式 = %.1fpt → %s" % (100 * d6b, "支持" if d6b < .1 else "外れ"))
    TN = cond("N", "tokyo", "kansai"); G = cond("N", "tokyo", "standard")
    if TN:
        k10 = rate(TN, "keihan")[0]; print("  P10 東京×N×関西の枠 京阪式 %s → %s" % (pct(k10), "支持" if k10 >= .5 else "外れ"))
        d10 = k10 - rate(G, "keihan")[0]; print("  P10' ゲートとの差 %+.1fpt → %s" % (100 * d10, "支持" if d10 >= .3 else "外れ"))
    # 再現性
    rep = [q for q in rows if q["stage"] == "repeat" and q["label"] in ("tokyo", "keihan", "not_tokyo")]
    pairs = 0; diff = 0
    for q in rep:
        o = [p for p in K if p["voice"] == q["voice"] and p["word"] == q["word"] and p["label"] in ("tokyo", "keihan", "not_tokyo")]
        if o: pairs += 1; diff += o[0]["label"] != q["label"]
    print("  P4 同じリクエスト2回で型が食い違った発話 %d/%d" % (diff, pairs))
    return rows

if __name__ == "__main__":
    main()

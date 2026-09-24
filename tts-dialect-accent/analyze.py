"""音声→拍の高さ→型の判定（PLAN.md 5節）。結果は data/utterances.csv

使い方: PROJECT_ID=... python analyze.py [--theta 1.5] [--stages gate,main,repeat]
"""
import os, sys, json, csv, argparse, numpy as np
import acoustic as A, corpus as C
HERE = os.path.dirname(os.path.abspath(__file__))
BUCKET = os.environ.get("GCS_BUCKET", os.environ.get("PROJECT_ID", "") + "-ttsdialect")

def requests():
    out = {}
    for l in open(os.path.join(HERE, "data", "requests.jsonl")):
        r = json.loads(l)
        if r.get("ok"): out[r["req"]] = r
    return [out[k] for k in sorted(out)]

def fetch(r):
    p = os.path.join(HERE, "data", "wav", f"req{r['req']:03d}.wav")
    if not os.path.exists(p):
        from google.cloud import storage
        os.makedirs(os.path.dirname(p), exist_ok=True)
        storage.Client().bucket(BUCKET).blob(f"wav/req{r['req']:03d}.wav").download_to_filename(p)
    return open(p, "rb").read()

def segments(x, sr, n_expected, thrs=(40, 35, 45, 30, 50)):
    """無音で区切る。n_expected 個にならなければ閾値を変えて試す。だめなら None"""
    fr = int(0.01 * sr)
    e = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, len(x) - fr, fr)])
    db = 20 * np.log10(e + 1e-9)
    for th in thrs:
        voiced = db > db.max() - th
        segs, st = [], None
        for i, v in enumerate(voiced):
            if v and st is None: st = i
            if not v and st is not None: segs.append([st, i]); st = None
        if st is not None: segs.append([st, len(voiced)])
        m = []
        for a, b in segs:                       # 250ms 未満の無音はつなぐ
            if m and a - m[-1][1] < 25: m[-1][1] = b
            else: m.append([a, b])
        m = [s for s in m if s[1] - s[0] >= 15]  # 150ms 未満は捨てる
        if len(m) == n_expected:
            return [(max(0, a * 0.01 - 0.05), b * 0.01 + 0.05) for a, b in m], th
    return None, None

def classify(cls, d1, d2, rng3, theta):
    s = lambda d: "+" if d > theta else ("-" if d < -theta else "0")
    s1, s2 = s(d1), s(d2)
    if cls == 1:
        if s1 == "+": return "tokyo"
        if rng3 < theta: return "keihan_candidate"
        return "neither"
    if rng3 < theta: return "flat"
    if cls in (2, 3):
        if s1 == "+" and s2 == "-": return "tokyo"
        if s1 == "-": return "keihan"
        return "neither"
    if cls == 4:
        if s1 == "-": return "tokyo"
        if s1 != "-" and (s2 == "+" or s1 == "+"): return "keihan"
        return "neither"
    if cls == 5:
        if s1 == "-": return "tokyo"
        if s1 == "+" or (s1 == "0" and s2 == "+"): return "keihan"
        return "neither"

def measure_request(r):
    """1リクエスト分の発話ごとの測定値（θ に依存しない部分）"""
    wav = fetch(r); x, sr = A.load(wav)
    n = 26
    segs, th = segments(x, sr, n)
    if segs is None: return [dict(req=r["req"], status="split_failed")]
    rng = A.voice_range(x, sr)
    frame_morae = C.FRAMES[r["frame"]][1]
    rows = []
    for i, (a, b) in enumerate(segs[1:-1]):
        w = r["words"][i]; cls, morae, src = C.WORDS[w]
        seg = x[int(a * sr):int(b * sr)]
        base = dict(req=r["req"], stage=r["stage"], voice=r["voice"], style=r["style"], frame=r["frame"],
                    pos=i + 1, word=w, cls=cls, keihan_src=src, split_db=th)
        try:
            res, _ = A.mora_pitch(seg, sr, morae + frame_morae, rng)
        except Exception as e:
            rows.append(dict(base, status="align_failed", note=str(e)[:80])); continue
        hz = [q[0] for q in res]
        if any(h != h for h in hz):
            rows.append(dict(base, status="unvoiced", voiced_ms=[round(q[1]) for q in res])); continue
        st = [12 * np.log2(h / 100) for h in hz]
        rows.append(dict(base, status="ok", m1=st[0], m2=st[1], m3=st[2], d1=st[1] - st[0], d2=st[2] - st[1],
                         rng3=max(st) - min(st), min_score=min(q[2] for q in res),
                         dur_ms=[round(1000 * (q[4] - q[3])) for q in res]))
    return rows

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--stages", default="gate,main,repeat")
    ap.add_argument("--theta", type=float, default=1.5); a = ap.parse_args()
    cache = os.path.join(HERE, "data", "measure.jsonl"); done = {}
    if os.path.exists(cache):
        for l in open(cache):
            q = json.loads(l); done.setdefault(q["req"], []).append(q)
    rows = []
    for r in requests():
        if r["stage"] not in a.stages.split(","): continue
        if r["req"] not in done:
            m = measure_request(r)
            with open(cache, "a") as f:
                for q in m: f.write(json.dumps(q, ensure_ascii=False, default=float) + "\n")
            done[r["req"]] = m
        rows += done[r["req"]]
    for q in rows:
        if q.get("status") == "ok": q["label"] = classify(q["cls"], q["d1"], q["d2"], q["rng3"], a.theta)
        else: q["label"] = q.get("status")
    keys = ["req","stage","voice","style","frame","pos","word","cls","keihan_src","status","label","m1","m2","m3","d1","d2","rng3","min_score","split_db"]
    with open(os.path.join(HERE, "data", "utterances.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, keys, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    return rows

if __name__ == "__main__":
    import collections
    rows = main()
    print(collections.Counter((q["stage"], q["label"]) for q in rows))

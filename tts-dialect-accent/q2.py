"""Q2：お嬢様と関西弁の読み分け（PLAN.md 7節）。
各文の最後の「わ」の高さ（拍の中央50%の平均）と、直前で声のある最も近い拍の高さの差（半音）、「わ」の長さ、「わ」の中の傾き。
文の区切りは Chirp 3 の「。」の時刻。拍の区間は MMS の強制アライメント。
"""
import os, json, csv, numpy as np
import acoustic as A, analyze as Z, stt
SENT = [
 ["i","e","so","n","na","ha","na","shi","wa","shi","ri","ma","se","n","wa"],
 ["ki","no","u","no","ko","to","de","shi","ta","ra","mo","u","wa","su","re","ma","shi","ta","wa"],
 ["a","no","o","mi","se","kyo","u","wa","o","ya","su","mi","de","su","wa"],
 ["a","me","ga","fu","t","ta","ra","ko","ma","ri","ma","su","wa"],
 ["a","shi","ta","wa","ha","ya","me","ni","ma","i","ri","ma","su","wa"],
 ["o","cha","de","shi","ta","ra","mo","u","i","ta","da","ki","ma","shi","ta","wa"],
 ["so","no","ke","n","wa","o","ko","to","wa","ri","shi","ma","su","wa"],
 ["ho","n","to","u","ni","bi","k","ku","ri","shi","ma","shi","ta","wa"],
 ["kyo","u","wa","mo","u","mu","ri","de","su","wa"],
 ["so","re","de","wa","ma","ta","ki","ma","su","wa"],
]
HERE = os.path.dirname(os.path.abspath(__file__))

def sentence_bounds(words, total):
    ends = [e for w, s, e in words if w.endswith("。")]
    if len(ends) != 10: return None
    starts = [0.0] + ends[:-1]
    return [(max(0, a - 0.02), min(total, b + 0.15)) for a, b in zip(starts, ends)]

def measure(r):
    wav = Z.fetch(r); x, sr = A.load(wav)
    cache = os.path.join(HERE, "data", "stt", f"req{r['req']:03d}.json")
    if os.path.exists(cache): text, words = json.load(open(cache))
    else:
        text, words = stt.transcribe(wav); os.makedirs(os.path.dirname(cache), exist_ok=True)
        json.dump([text, words], open(cache, "w"), ensure_ascii=False)
    b = sentence_bounds(words, len(x) / sr)
    if b is None: return [dict(req=r["req"], status="split_failed", transcript=text)]
    rng = A.voice_range(x, sr); rows = []
    for k, ((a, e), morae) in enumerate(zip(b, SENT)):
        seg = x[int(a * sr):int(e * sr)]
        t, f = A.pitch_track(seg, sr, *rng); f = A.fix_octave(f)
        try: spans = A.align(seg, sr, morae)
        except Exception as ex:
            rows.append(dict(req=r["req"], sent=k + 1, status="align_failed")); continue
        st = [cs[0][0] for cs in spans]; en = spans[-1][-1][1]
        def mora_mean(i):
            lo = st[i]; hi = st[i + 1] if i + 1 < len(st) else en
            L = hi - lo; sel = (t >= lo + L * .25) & (t <= hi - L * .25) & (f > 0)
            return 12 * np.log2(np.mean(f[sel]) / 100) if sel.sum() >= 3 else np.nan
        wa = mora_mean(len(morae) - 1)
        prev, pi = np.nan, None
        for i in range(len(morae) - 2, -1, -1):
            v = mora_mean(i)
            if v == v: prev, pi = v, i; break
        lo = st[-1]; sel = (t >= lo) & (t <= en) & (f > 0)
        slope = np.polyfit(t[sel], 12 * np.log2(f[sel] / 100), 1)[0] if sel.sum() >= 5 else np.nan
        rows.append(dict(req=r["req"], voice=r["voice"], style=r["style"], take=r["seed"], sent=k + 1, status="ok" if wa == wa and prev == prev else "unvoiced",
                         wa=wa, prev=prev, prev_mora=morae[pi] if pi is not None else None, diff=wa - prev if wa == wa and prev == prev else np.nan,
                         wa_ms=round(1000 * (en - lo)), slope=slope))
    return rows

if __name__ == "__main__":
    rows = []
    for r in Z.requests():
        if r["stage"] == "q2": rows += measure(r)
    keys = ["req","voice","style","take","sent","status","wa","prev","prev_mora","diff","wa_ms","slope"]
    with open(os.path.join(HERE, "data", "q2_wa.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, keys, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print(len(rows), "rows")

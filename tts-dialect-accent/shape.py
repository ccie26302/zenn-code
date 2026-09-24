"""型の形で判定する（PLAN v5）。
名詞2拍＋「が」の3拍それぞれで 25/50/75% の時点の F0（半音）を取り 9 次元にし、平均を引く。
お手本は、陰性ゲート（東京ラベル×指示なし×標準の枠）の実音声から作る3つの形：
  平板（1類）/ 尾高（2・3類）/ 頭高（4・5類）
京阪式の2・3類は頭高の形、5類は尾高の形になる（東京と入れ替わる）ので、同じお手本で判定できる。
"""
import numpy as np, acoustic as A

SHAPE_OF_TOKYO = {1: "heiban", 2: "odaka", 3: "odaka", 4: "atamadaka", 5: "atamadaka"}
SHAPE_OF_KEIHAN = {2: "atamadaka", 3: "atamadaka", 5: "odaka"}   # 1類(高高高)と4類(低低高)は東京の形に対応が無い

def vector(seg, sr, morae, rng):
    t, f = A.pitch_track(seg, sr, *rng); f = A.fix_octave(f)
    spans = A.align(seg, sr, morae)
    starts = [cs[0][0] for cs in spans]
    v = np.where(f > 0, 12 * np.log2(np.where(f > 0, f, 1) / 100), np.nan)
    ok = ~np.isnan(v)
    if ok.sum() < 10: return None, "unvoiced"
    pts = []
    for k in range(3):
        a, b = starts[k], starts[k + 1]
        for q in (.25, .5, .75): pts.append(a + (b - a) * q)
    # 無声区間は線形補間（区間の外側は使わない）
    lo, hi = starts[0], starts[3]
    sel = ok & (t >= lo - 0.03) & (t <= hi + 0.03)
    if sel.sum() < 8: return None, "unvoiced"
    near = [np.min(np.abs(t[sel] - p)) for p in pts]
    if sum(d > 0.04 for d in near) > 3: return None, "unvoiced"
    vec = np.interp(pts, t[sel], v[sel])
    return vec - vec.mean(), "ok"

def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])

def templates(vecs_by_shape):
    return {s: np.mean(v, axis=0) for s, v in vecs_by_shape.items() if len(v)}

def nearest(vec, T):
    sc = {s: corr(vec, m) for s, m in T.items()}
    best = max(sc, key=sc.get)
    return best, sc

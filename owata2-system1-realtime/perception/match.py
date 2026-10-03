"""テンプレート照合による自機検出(スクロールに依存しない)。
score = Dice = 2|T∩F| / (|T| + |F の窓内画素数|)。FFT で全位置を一度に計算する。"""
import os, numpy as np
from scipy.signal import fftconvolve
HERE = os.path.dirname(__file__)
_t = np.load(os.path.join(HERE, "player_templates.npz")); TPLS = [_t[k].astype(np.float32) for k in _t.files]

def binarize(rgb_sum):
    b = (rgb_sum < 300).astype(np.float32)
    b[:41, 520:] = 0          # R:Retry 欄
    return b

def window_sum(F, h, w):
    ii = np.pad(F.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return ii[h:, w:] - ii[:-h, w:] - ii[h:, :-w] + ii[:-h, :-w]

def detect(rgb_sum, thr=0.43):   # M1: 生存の最低 0.49 と自機なしの最大 0.36 の間
    F = binarize(rgb_sum); best = (0, None, None)
    for ti, T in enumerate(TPLS):
        h, w = T.shape
        tf = fftconvolve(F, T[::-1, ::-1], mode="valid")
        fw = window_sum(F, h, w)
        dice = 2 * tf / (T.sum() + fw + 1e-6)
        k = np.unravel_index(np.argmax(dice), dice.shape)
        if dice[k] > best[0]: best = (float(dice[k]), (int(k[1]), int(k[0]), w, h), ti)
    score, box, ti = best
    if box is None or score < thr: return {"player": None, "score": round(score, 3)}
    x, y, w, h = box
    return {"player": {"x": x + w // 2, "y": y + h // 2, "box": [x, y, x + w - 1, y + h - 1], "tpl": ti}, "score": round(score, 3)}


def camera_shift(prev_sum, cur_sum, mask_boxes=(), max_dx=120, max_dy=40):
    """前コマ→今コマで背景が何 px ずれたか(カメラの移動量の符号反転)。自機などの領域は隠して位相相関で求める。
    戻り値 (dx, dy, peak): 今コマの背景 = 前コマの背景を (dx, dy) だけ動かしたもの。"""
    A = binarize(prev_sum); B = binarize(cur_sum)
    for (x0, y0, x1, y1) in mask_boxes:
        A[max(0, y0 - 4):y1 + 5, max(0, x0 - 4):x1 + 5] = 0; B[max(0, y0 - 4):y1 + 5, max(0, x0 - 4):x1 + 5] = 0
    if A.sum() < 50 or B.sum() < 50: return (0, 0, 0.0)
    fa = np.fft.rfft2(A); fb = np.fft.rfft2(B)
    cps = fb * np.conj(fa); cps /= np.abs(cps) + 1e-9
    r = np.fft.irfft2(cps, s=A.shape)
    H, W = A.shape
    # 探索範囲を制限
    cand = np.full_like(r, -1e9)
    for dy in range(-max_dy, max_dy + 1):
        for dx in (slice(0, max_dx + 1), slice(W - max_dx, W)):
            cand[dy % H, dx] = r[dy % H, dx]
    k = np.unravel_index(np.argmax(cand), cand.shape)
    dy, dx = int(k[0]), int(k[1])
    if dy > H // 2: dy -= H
    if dx > W // 2: dx -= W
    return (dx, dy, float(r[k]))


# ---- 足場と地面(型付き状態のための追加の目) ----
_PLAT = None
def set_platform_template(bg_sum, box=(304, 245, 359, 258)):
    """1面の背景から足場「[===]」の形を切り出す(開発用ステージ)。"""
    global _PLAT
    x0, y0, x1, y1 = box
    _PLAT = (bg_sum[y0:y1 + 1, x0:x1 + 1] < 300).astype(np.float32)

def detect_platform(rgb_sum, thr=0.6):
    if _PLAT is None: return None
    F = binarize(rgb_sum); h, w = _PLAT.shape
    tf = fftconvolve(F, _PLAT[::-1, ::-1], mode="valid"); fw = window_sum(F, h, w)
    dice = 2 * tf / (_PLAT.sum() + fw + 1e-6)
    k = np.unravel_index(np.argmax(dice), dice.shape)
    if dice[k] < thr: return None
    return {"x0": int(k[1]), "x1": int(k[1] + w - 1), "y0": int(k[0]), "y1": int(k[0] + h - 1), "score": round(float(dice[k]), 3)}

def ground_ahead(rgb_sum, player, look=260):
    """自機の足元の高さで、右(と左)に地面の線がどこまで続くか。途切れた先にトゲ(△)があるか。
    足元の行 = 自機の枠の下端の少し上〜少し下(枠の下端が地面の線と重なるため)。"""
    if not player: return None
    x0, y0, x1, y1 = player["box"]
    H, W = rgb_sum.shape
    line = (rgb_sum < 650)                   # 地面の線(灰色を含む)
    r0, r1 = max(0, y1 - 2), min(H, y1 + 7)
    rows = line[r0:r1].any(axis=0)
    def run(direction):
        xs = range(x1 + 1, min(W, x1 + 1 + look)) if direction > 0 else range(x0 - 1, max(-1, x0 - 1 - look), -1)
        gap = 0
        for x in xs:
            if rows[x]: gap = 0
            else:
                gap += 1
                if gap >= 6: return abs(x - (x1 if direction > 0 else x0)) - 5
        return None                          # 見える範囲では途切れない
    right = run(+1); left = run(-1)
    # 向こう岸(2026-10-02): 右の途切れの先で、地面の線が 10px 以上続けてまた始まる位置(自機の右端からの距離)
    far = None
    if right is not None:
        x = x1 + right + 6; run_on = 0
        while x < W:
            run_on = run_on + 1 if rows[x] else 0
            if run_on >= 10: far = x - 9 - x1; break
            x += 1
    spikes = None
    if right is not None:
        sx = x1 + right + 6
        band = rgb_sum[r0:min(H, r0 + 60), sx:min(W, sx + 220)] < 300
        spikes = bool(band.sum() > 40)
    under = line[max(0, y1 - 1):min(H, y1 + 4), max(0, x0):x1 + 1].any(axis=0)
    on_ground = bool(under.mean() >= 0.6) if under.size else False
    if not on_ground: right = left = spikes = far = None      # 空中では崖までの距離に意味がない
    return {"edge_right_px": right, "edge_left_px": left, "spikes_after_right_edge": spikes, "far_ground_px": far, "on_ground": on_ground}


# 目の追加(B7): トゲ「△」の列。1個の形で画面全体を照合し、横に並んだものを列にまとめる
_SPK = np.load(os.path.join(HERE, "spike_template.npy")).astype(np.float32)

def detect_spikes(rgb_sum, thr=0.8, min_count=3):
    """戻り値: [{y: 底辺の行, x0, x1, n}](画面座標、y の小さい=上から順)。"""
    F = binarize(rgb_sum); h, w = _SPK.shape
    tf = fftconvolve(F, _SPK[::-1, ::-1], mode="valid")
    dice = 2 * tf / (_SPK.sum() + window_sum(F, h, w) + 1e-6)
    ys, xs = np.where(dice >= thr)
    if not len(ys): return []
    order = np.argsort(-dice[ys, xs]); taken = []
    for i in order:                                   # 近すぎる重複を間引く(1個 = 幅 w)
        y, x = int(ys[i]), int(xs[i])
        if all(abs(y - ty) > 4 or abs(x - tx) >= w - 2 for ty, tx in taken): taken.append((y, x))
    rows = {}
    for y, x in taken:
        key = next((k for k in rows if abs(k - y) <= 3), y); rows.setdefault(key, []).append(x)
    out = []
    for y, xl in rows.items():
        if len(xl) < min_count: continue
        out.append({"y": y + h - 1, "x0": int(min(xl)), "x1": int(max(xl)) + w - 1, "n": len(xl)})
    return sorted(out, key=lambda r: r["y"])

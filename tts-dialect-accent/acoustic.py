"""拍ごとの高さを測る。
1) Chirp 3 の語の時刻で文を切り出す
2) MMS（torchaudio の MMS_FA）でローマ字の文字単位に強制アライメント
3) 各拍の母音の中央50%で F0（parselmouth）の平均を半音で出す
"""
import io, numpy as np, soundfile as sf, torch, torchaudio, parselmouth
from torchaudio.pipelines import MMS_FA as B

_model = None
def _mms():
    global _model
    if _model is None: _model = B.get_model().eval()
    return _model

KANA = {  # 使う語と枠のローマ字(拍ごと)
}
VOWELS = set("aiueo")

def load(wav_bytes):
    x, sr = sf.read(io.BytesIO(wav_bytes)); return x.astype(np.float32), sr

def pitch_track(x, sr, floor, ceil):
    p = parselmouth.Sound(x, sampling_frequency=sr).to_pitch_ac(time_step=0.005, pitch_floor=floor, pitch_ceiling=ceil)
    f = p.selected_array["frequency"]; t = p.xs()
    s = parselmouth.Sound(x, sampling_frequency=sr).to_intensity(time_step=0.005)
    it = np.interp(t, s.xs(), s.values[0]); f = np.where(it < it.max() - 25, 0, f)   # 弱いフレームを除く
    return t, f

def voice_range(x, sr):
    """2段階: まず広い範囲で取り、15%点×0.75〜85%点×1.5 に絞る"""
    t, f = pitch_track(x, sr, 50, 600); v = f[f > 0]
    if len(v) < 20: return 60, 500
    return max(40, np.percentile(v, 15) * 0.75), min(800, np.percentile(v, 85) * 1.5)

def fix_octave(f):
    """前後の中央値から1オクターブ近く跳ねた点を半分・倍に戻す"""
    g = f.copy(); v = np.where(g > 0)[0]
    if len(v) < 5: return g
    med = np.median(g[v])
    for i in v:
        r = g[i] / med
        if r > 1.8: g[i] /= 2
        elif r < 0.55: g[i] *= 2
    return g

def align(seg, sr, morae):
    """morae: ["na","mi","ga", ...] → 各文字の区間(秒)。MMS はローマ字小文字の文字単位"""
    y = torch.tensor(seg)[None]
    if sr != B.sample_rate: y = torchaudio.functional.resample(y, sr, B.sample_rate)
    with torch.inference_mode():
        em, _ = _mms()(y)
    dic = B.get_dict(star=None)
    chars = "".join(morae)
    tokens = [dic[c] for c in chars]
    ali, scores = torchaudio.functional.forced_align(em, torch.tensor([tokens], dtype=torch.int32), blank=0)
    spans = torchaudio.functional.merge_tokens(ali[0], scores[0].exp())
    ratio = y.shape[1] / em.shape[1] / B.sample_rate
    out = []; k = 0
    for m in morae:
        cs = spans[k:k + len(m)]; k += len(m)
        out.append([(s.start * ratio, s.end * ratio, float(s.score)) for s in cs])
    return out

def mora_pitch(seg, sr, morae, rng, n_measure=3):
    """先頭 n_measure 拍（名詞2拍＋が）について、拍の区間（その拍の最初の文字の開始〜次の拍の最初の文字の開始）の
    中央50%にある有声フレームの F0 平均(Hz)、有声長(ms)、アライメントの最小スコアを返す"""
    t, f = pitch_track(seg, sr, *rng); f = fix_octave(f)
    spans = align(seg, sr, morae)
    starts = [cs[0][0] for cs in spans]
    res = []
    for k in range(n_measure):
        a = starts[k]; b = starts[k + 1] if k + 1 < len(starts) else spans[k][-1][1]
        L = b - a; a2, b2 = a + L * .25, b - L * .25
        sel = (t >= a2) & (t <= b2) & (f > 0)
        voiced_ms = 1000 * np.sum((t >= a) & (t <= b) & (f > 0)) * 0.005
        sc = min(c[2] for c in spans[k])
        res.append((float(np.mean(f[sel])) if sel.sum() >= 3 else np.nan, voiced_ms, sc, a, b))
    return res, spans

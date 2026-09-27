"""Q2 探索：文章全体の長さと声の高さ（中央値、半音）"""
import os, numpy as np, acoustic as A, analyze as Z
for r in Z.requests():
    if r["stage"] != "q2": continue
    x, sr = A.load(Z.fetch(r)); t, f = A.pitch_track(x, sr, 60, 500); f = A.fix_octave(f); v = 12 * np.log2(f[f > 0] / 100)
    print(r["req"], r["voice"], r["style"], r["seed"], "秒 %.1f" % (len(x) / sr), "高さの中央 %.1f" % np.median(v), "幅 %.1f" % (np.percentile(v, 95) - np.percentile(v, 5)))

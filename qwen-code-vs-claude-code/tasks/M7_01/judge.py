import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; from mlib import probe, dur, ebur
w = sys.argv[1]; p = os.path.join(w, "podcast_norm.wav")
if ck("podcast_norm.wav がある", os.path.exists(p)):
    I, TP = ebur(p); d0 = dur(probe(os.path.join(w, "podcast.wav"))); d = dur(probe(p))
    ck("統合ラウドネス -16±1 LUFS", I is not None and abs(I + 16) <= 1, I)
    ck("トゥルーピーク -1.5 dBTP 以下", TP is not None and TP <= -1.5, TP)
    ck("長さが同じ(±0.1秒)", abs(d - d0) <= 0.1, (d0, d))
done()

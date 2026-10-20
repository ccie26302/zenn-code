import os, sys, subprocess; sys.path.insert(0, "/tasks")
from jlib import ck, done; from mlib import probe, stream, dur
w = sys.argv[1]; p = os.path.join(w, "fast.mp4")
def sdur(pr, kind):
    s = stream(pr, kind); return float(s.get("duration", 0)) if s else 0.0
if ck("fast.mp4 がある", os.path.exists(p)):
    pr = probe(p); dv, da = sdur(pr, "video"), sdur(pr, "audio")
    ck("映像が 10 秒(±0.15)", abs(dv - 10.0) <= 0.15, dv)
    ck("音声が 10 秒(±0.15)", abs(da - 10.0) <= 0.15, da)
    ck("映像と音声のずれが 0.2 秒以内", abs(dv - da) <= 0.2, abs(dv - da))
done()

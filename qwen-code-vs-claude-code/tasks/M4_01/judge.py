import os, subprocess, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; from mlib import probe, stream, dur, frame_gray
w = sys.argv[1]; p = os.path.join(w, "burned.mp4"); src = os.path.join(w, "clip.mp4")
def ahash(f):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-map", "0:a:0", "-c", "copy", "-f", "hash", "-hash", "md5", "-"], capture_output=True, text=True); return r.stdout.strip()
def diff(t):
    a = frame_gray(src, t, 128, 24, "1280:180:0:540"); b = frame_gray(p, t, 128, 24, "1280:180:0:540")
    return sum(abs(x - y) for x, y in zip(a, b)) / max(1, len(a)) if a and b and len(a) == len(b) else 999
if ck("burned.mp4 がある", os.path.exists(p)):
    pr = probe(p); ck("映像と音声がある", stream(pr, "video") and stream(pr, "audio")); ck("長さが同じ(±0.2秒)", abs(dur(pr) - dur(probe(src))) <= 0.2, dur(pr))
    ck("字幕の時間帯は下部が変わっている", diff(1.5) > 3 and diff(4.5) > 3, (round(diff(1.5), 1), round(diff(4.5), 1)))
    ck("字幕の無い時間帯は下部がほぼ同じ", diff(3.0) < 3, round(diff(3.0), 1))
    ck("音声は再エンコードしていない(パケットのハッシュが同じ)", ahash(p) == ahash(src))
done()

import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; from mlib import probe, stream, dur
w = sys.argv[1]; p = os.path.join(w, "demo.gif")
if ck("demo.gif がある", os.path.exists(p)):
    pr = probe(p); v = stream(pr, "video") or {}
    ck("GIF", v.get("codec_name") == "gif", v.get("codec_name")); ck("幅 480、縦は比率どおり(270±2)", v.get("width") == 480 and abs((v.get("height") or 0) - 270) <= 2, (v.get("width"), v.get("height")))
    ck("1MB 以下", os.path.getsize(p) <= 1024 * 1024, os.path.getsize(p))
    ck("動画の全体(長さ 8秒の 90% 以上)", dur(pr) >= 7.2, dur(pr))
done()

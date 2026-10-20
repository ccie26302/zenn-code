import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; from mlib import probe, stream, dur, frame_gray
w = sys.argv[1]; p = os.path.join(w, "vertical.mp4")
if ck("vertical.mp4 がある", os.path.exists(p)):
    pr = probe(p); v = stream(pr, "video")
    ck("1080x1920", v and (v.get("width"), v.get("height")) == (1080, 1920), v and (v.get("width"), v.get("height")))
    ck("音声が残っている", stream(pr, "audio") is not None)
    ck("長さが元と同じ(±0.2秒)", abs(dur(pr) - 8.0) <= 0.2, dur(pr))
    # 元は 16:9。1080 幅なら映像の高さは 608。上下の帯はそれぞれ約656
    top = frame_gray(p, 2, 54, 30, "1080:500:0:0"); mid = frame_gray(p, 2, 54, 30, "1080:500:0:710")
    ck("上の帯が黒", top and max(top) <= 24, top and max(top))
    ck("中央に映像がある(黒ではない)", mid and sum(mid) / len(mid) > 40, mid and sum(mid) / len(mid))
done()

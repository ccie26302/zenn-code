import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; from mlib import probe, stream, dur
w = sys.argv[1]; p = os.path.join(w, "audio.wav")
if ck("audio.wav がある", os.path.exists(p)):
    pr = probe(p); a = stream(pr, "audio")
    ck("映像がない", stream(pr, "video") is None)
    ck("pcm_s16le", a and a.get("codec_name") == "pcm_s16le", a and a.get("codec_name"))
    ck("16000Hz", a and a.get("sample_rate") == "16000", a and a.get("sample_rate"))
    ck("モノラル", a and a.get("channels") == 1, a and a.get("channels"))
    ck("長さが元と同じ(±0.1秒)", abs(dur(pr) - 10.0) <= 0.1, dur(pr))
done()

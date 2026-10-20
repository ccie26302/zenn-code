import os, re, sys; sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done; from setup import SCRIPT
w = sys.argv[1]; p = os.path.join(w, "meeting.srt")
def words(s): return re.findall(r"[a-z0-9']+", s.lower())
def wer(ref, hyp):
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
    return d[len(hyp)] / max(1, len(ref))
def ts(x): h, m, s = x.replace(",", ".").split(":"); return int(h) * 3600 + int(m) * 60 + float(s)
if ck("meeting.srt がある", os.path.exists(p)):
    t = open(p, encoding="utf-8", errors="replace").read().replace("\r", "")
    cues = re.findall(r"(?m)^\d+\n(\d\d:\d\d:\d\d[,.]\d\d\d) --> (\d\d:\d\d:\d\d[,.]\d\d\d)\n((?:.+\n?)+)", t)
    ck("SRT の字幕が1つ以上ある", len(cues) >= 1, len(cues))
    times = [(ts(a), ts(b)) for a, b, _ in cues]
    ck("時刻が単調に増え、終わりが始まりより後", all(a < b for a, b in times) and all(times[i][0] >= times[i - 1][0] for i in range(1, len(times))), times[:3])
    hyp = words(" ".join(c[2] for c in cues)); ref = words(" ".join(SCRIPT)); e = wer(ref, hyp)
    ck("台本との単語誤り率が 30% 以下", e <= 0.30, round(e, 3))
done()

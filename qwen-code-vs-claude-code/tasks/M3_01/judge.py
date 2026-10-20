import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; from mlib import probe, dur, silences, silence_list
w = sys.argv[1]; p = os.path.join(w, "cut.wav")
src = os.path.join(w, "talk.wav"); orig = dur(probe(src))
LONG = silence_list(src, "-30dB", 0.5)          # 元の音声で実際に測った、0.5秒以上の無音
if ck("cut.wav がある", os.path.exists(p)):
    d = dur(probe(p)); ends, starts = silences(p, "-30dB", 0.5)
    ck("0.5秒以上の無音が残っていない", starts == 0, starts)
    lo = orig - sum(LONG) - 0.25; hi = orig - sum(LONG) + 0.5 * len(LONG)
    ck("長さが妥当(話を削らず、長い無音を削った)", lo <= d <= hi, "%.2f (%.2f〜%.2f、元の長い無音 %s)" % (d, lo, hi, LONG))
done()

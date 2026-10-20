import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; from mlib import probe, dur, packets
w = sys.argv[1]; p = os.path.join(w, "full.mp4"); parts = [os.path.join(w, "part%d.mp4" % i) for i in (1, 2, 3)]
if ck("full.mp4 がある", os.path.exists(p)):
    ck("長さが合計(±0.15秒)", abs(dur(probe(p)) - sum(dur(probe(x)) for x in parts)) <= 0.15, dur(probe(p)))
    segs = [packets(x) for x in parts]; exp = sum(segs, []); got = packets(p)
    firsts = {sum(len(s) for s in segs[:i]) for i in range(len(segs))}     # 各パートの先頭(設定情報が付け直されて少し大きくなる)
    bad = [i for i, (a, b) in enumerate(zip(exp, got)) if (a != b and i not in firsts) or (i in firsts and abs(a - b) > 200)]
    ck("映像のパケットが元と同じ(再エンコードしていない。各パートの先頭は200バイトまでの差を認める)", len(got) == len(exp) and not bad, (len(got), len(exp), bad[:5]))
done()

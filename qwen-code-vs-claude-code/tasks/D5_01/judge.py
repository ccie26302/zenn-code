import os, re, sys; sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done; from setup import PAGES
w = sys.argv[1]; p = os.path.join(w, "scan.txt")
def norm(s): return re.sub(r"\s+", " ", s.lower()).strip()
def cer(ref, hyp):
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1): prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
    return d[len(hyp)] / max(1, len(ref))
if ck("scan.txt がある", os.path.exists(p)):
    hyp = norm(open(p, encoding="utf-8", errors="replace").read()); ref = norm(" ".join(" ".join(x) for x in PAGES))
    e = cer(ref, hyp); ck("文字誤り率 10% 以下", e <= 0.10, round(e, 3))
    ck("ページ順(各ページの見出しの順)", 0 <= hyp.find("quarterly operations") < hyp.find("security review") < hyp.find("next steps"), [hyp.find(x) for x in ("quarterly operations", "security review", "next steps")])
done()

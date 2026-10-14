import os, sys
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done
from setup import gen
w = sys.argv[1]
files, sums, status = gen()
exp = ["%s %s" % (status[p], p) for p in sorted(status)]
ck("extracted/ に展開されている", all(os.path.exists(os.path.join(w, "extracted", p)) for p in files), "")
q = os.path.join(w, "verify.txt")
if ck("verify.txt がある", os.path.exists(q)):
    got = [l.strip() for l in open(q) if l.strip()]
    ck("結果が正しい", sorted(got) == sorted(exp), sorted(set(got) ^ set(exp))[:5])
    ck("並び順", got == exp)
done()

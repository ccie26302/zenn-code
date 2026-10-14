import os, sys
from collections import defaultdict
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done, files
from setup import gen
w = sys.argv[1]
groups = defaultdict(list)
for rel, b in gen(): groups[b].append(rel)
keep, move = {}, {}
for b, rels in groups.items():
    rels = sorted(rels); keep[rels[0]] = b
    for r in rels[1:]: move[r] = b
d = files(os.path.join(w, "docs")) if os.path.isdir(os.path.join(w, "docs")) else []
u = files(os.path.join(w, "duplicates")) if os.path.isdir(os.path.join(w, "duplicates")) else []
ck("docs/ に残すべきものだけが残る", set(d) == set(keep), sorted(set(d) ^ set(keep))[:5])
ck("duplicates/ に移すべきものが相対パスのまま入る", set(u) == set(move), sorted(set(u) ^ set(move))[:5])
bad = [r for r in keep if r in d and open(os.path.join(w, "docs", r), "rb").read() != keep[r]]
bad += [r for r in move if r in u and open(os.path.join(w, "duplicates", r), "rb").read() != move[r]]
ck("中身が変わっていない(消えていない)", not bad, bad[:5])
done()

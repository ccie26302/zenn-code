import os, sys
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done
from setup import gen
w = sys.argv[1]
items = sorted(gen(), key=lambda t: (t[2], t[0]))
expect = {"%03d_%04d-%02d-%02d.jpg" % (i + 1, *t[2]): t[1] for i, t in enumerate(items)}
got = sorted(os.listdir(os.path.join(w, "photos")))
ck("ファイル名の集合が期待どおり", set(got) == set(expect), sorted(set(got) ^ set(expect))[:6])
bad = [n for n in expect if n in got and open(os.path.join(w, "photos", n), "rb").read() != expect[n]]
ck("各連番に正しい写真が入っている", not bad, bad[:5])
done()

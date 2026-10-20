import os, sys; sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done; from setup import gen
from PIL import Image
w = sys.argv[1]; exp = {}; cnt = {}
for n, dt, c in sorted(gen()):
    if dt is None: exp["no_exif/" + n] = c; continue
    b = dt.replace(":", "").replace(" ", "_"); cnt[b] = cnt.get(b, 0) + 1
    exp["sorted/%s%s.jpg" % (b, "" if cnt[b] == 1 else "_%d" % cnt[b])] = c
got = {}
for sub in ("sorted", "no_exif"):
    dd = os.path.join(w, sub)
    for f in (os.listdir(dd) if os.path.isdir(dd) else []): got[sub + "/" + f] = Image.open(os.path.join(dd, f)).convert("RGB").getpixel((10, 10))
ck("ファイル名の集合が期待どおり", set(got) == set(exp), sorted(set(got) ^ set(exp))[:4])
ck("各ファイルの中身(色)が対応している", all(p in got and max(abs(a - b) for a, b in zip(got[p], c)) <= 6 for p, c in exp.items()))
ck("camera/ が空", not os.listdir(os.path.join(w, "camera")) if os.path.isdir(os.path.join(w, "camera")) else True)
done()

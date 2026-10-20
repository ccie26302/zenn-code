import hashlib, os, sys; sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done; from setup import ROWS
w = sys.argv[1]
ck("元のファイルが変わっていない", all(open(os.path.join(w, "legacy", n), "rb").read() == t.encode("cp932") for n, t in ROWS.items()))
for n, t in ROWS.items():
    p = os.path.join(w, "utf8", n)
    ck("%s が UTF-8(BOM なし)で中身が正しい" % n, os.path.exists(p) and open(p, "rb").read() == t.encode("utf-8"), (open(p, "rb").read()[:20] if os.path.exists(p) else "無い"))
done()

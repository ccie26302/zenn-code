import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
ID = os.environ["ID"]; bs = G.buckets()
ck("qg-ID-tmp-a と tmp-b が消えている", not ({"qg-%s-tmp-a" % ID, "qg-%s-tmp-b" % ID} & set(bs)), [b for b in bs if "-tmp-" in b])
for d in ("tmpl", "temp", "keep-tmp", "tmp"):
    n = "qg-%s-%s" % (ID, d)
    ck("おとり %s が中身ごと残っている" % d, n in bs and any("data.txt" in (o.get("name") or o.get("url") or "") for o in G.objects(n)))
done()

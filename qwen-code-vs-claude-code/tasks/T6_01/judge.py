import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G; from tfmeta import created, meta
w = sys.argv[1]; ID = os.environ["ID"]; inf = os.path.join(w, "infra")
for n in ("keep", "stay"):
    b = "qg-%s-%s" % (ID, n); ck("%s が作り直されずに残っている" % n, created(b) and created(b) == meta(w).get(b), (created(b), meta(w).get(b)))
addrs = G.tf_state_addrs(inf)
ck("keep は state に無く、stay は state にある", any(a.endswith("google_storage_bucket.stay") for a in addrs) and not any("keep" in a for a in addrs), addrs)
rc, out = G.tf_plan(inf); ck("terraform plan で差分なし", rc == 0, out[-300:])
done()

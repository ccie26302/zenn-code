import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G; from tfmeta import created, meta
w = sys.argv[1]; ID = os.environ["ID"]; inf = os.path.join(w, "infra")
for n in ("raw", "curated"):
    b = "qg-%s-%s" % (ID, n); ck("%s を作り直していない" % n, created(b) and created(b) == meta(w).get(b), (created(b), meta(w).get(b)))
    ck("%s のラベルが元のまま" % n, (G.bucket(b) or {}).get("labels") == {"layer": n}, (G.bucket(b) or {}).get("labels"))
md = os.path.join(inf, "modules", "bucket")
ck("modules/bucket に .tf がある", os.path.isdir(md) and any(f.endswith(".tf") for f in os.listdir(md)))
addrs = G.tf_state_addrs(inf); ck("state の2つのバケットがモジュールの下にある", sum(1 for a in addrs if a.startswith("module.") and "google_storage_bucket." in a) == 2 and not any(a.startswith("google_storage_bucket.") for a in addrs), addrs)
rc, out = G.tf_plan(inf); ck("terraform plan で差分なし", rc == 0, out[-300:])
done()

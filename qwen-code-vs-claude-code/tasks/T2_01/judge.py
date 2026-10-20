import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G; from tfmeta import created, meta
w = sys.argv[1]; ID = os.environ["ID"]; n = "qg-%s-legacy" % ID; inf = os.path.join(w, "infra")
ck("作り直していない(作成時刻が同じ)", created(n) and created(n) == meta(w).get(n), (created(n), meta(w).get(n)))
b = G.bucket(n) or {}; ck("ラベルとバージョニングが元のまま", b.get("labels") == {"app": "legacy", "owner": "ops"} and b.get("versioning_enabled") is True, (b.get("labels"), b.get("versioning_enabled")))
ck("state にバケットがある", any("google_storage_bucket." in a for a in G.tf_state_addrs(inf)), G.tf_state_addrs(inf))
rc, out = G.tf_plan(inf); ck("terraform plan で差分なし", rc == 0, out[-300:])
done()

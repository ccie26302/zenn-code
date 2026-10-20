import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
w = sys.argv[1]; ID = os.environ["ID"]; inf = os.path.join(w, "infra"); b = G.bucket("qg-%s-fix" % ID)
if ck("バケットがある", b):
    ck("asia-northeast1", (b.get("location") or "").lower() == "asia-northeast1", b.get("location"))
    ck("均一なアクセス", b.get("uniform_bucket_level_access") is True)
    ck("ラベル purpose=billing-export", b.get("labels") == {"purpose": "billing-export"}, b.get("labels"))
    rc, out = G.tf_plan(inf); ck("terraform plan で差分なし", rc == 0, out[-300:])
done()

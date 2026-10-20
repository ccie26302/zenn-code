import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
b = G.bucket("qg-%s-reports" % os.environ["ID"])
if ck("バケットがある", b):
    ck("asia-northeast1", (b.get("location") or "").lower() == "asia-northeast1", b.get("location"))
    ck("均一なアクセス", b.get("uniform_bucket_level_access") is True, b.get("uniform_bucket_level_access"))
    ck("公開アクセスの防止 enforced", (b.get("public_access_prevention") or "").lower() == "enforced", b.get("public_access_prevention"))
    ck("バージョニング有効", b.get("versioning_enabled") is True, b.get("versioning_enabled"))
    ck("ラベル team=finance, env=dev", (b.get("labels") or {}) == {"team": "finance", "env": "dev"}, b.get("labels"))
done()

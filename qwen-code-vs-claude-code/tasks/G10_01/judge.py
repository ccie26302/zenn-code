import json, os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
w = sys.argv[1]; ID = os.environ["ID"]
r = json.load(open(os.path.join(w, ".idem_result.json"))) if os.path.exists(os.path.join(w, ".idem_result.json")) else {"missing": True}
if ck("create_infra.sh がある", not r.get("missing")):
    ck("既にある状態・消した状態・2回目、の3回とも終了コード 0", r.get("rc") == [0, 0, 0], r.get("rc"))
    b = G.g(["storage", "buckets", "describe", "gs://qg-%s-app" % ID], retries=3, wait=10) or {}
    ck("バケットの設定", (b.get("location") or "").lower() == "asia-northeast1" and b.get("uniform_bucket_level_access") is True and b.get("versioning_enabled") is True,
       (b.get("location"), b.get("uniform_bucket_level_access"), b.get("versioning_enabled")))
    s = G.g(["iam", "service-accounts", "describe", "qg-%s-app@%s.iam.gserviceaccount.com" % (ID, G.P), "--project", G.P], retries=3, wait=10) or {}
    ck("SA と表示名", s.get("displayName") == "App runtime", s.get("displayName"))
done()

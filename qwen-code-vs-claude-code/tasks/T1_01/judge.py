import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
w = sys.argv[1]; ID = os.environ["ID"]; inf = os.path.join(w, "infra"); b = G.bucket("qg-%s-tf" % ID)
m = "serviceAccount:qg-%s-tf@%s.iam.gserviceaccount.com" % (ID, G.P)
if ck("バケットがある", b):
    ck("バケットの設定(地域・均一・ラベル)", (b.get("location") or "").lower() == "asia-northeast1" and b.get("uniform_bucket_level_access") is True and (b.get("labels") or {}).get("managed_by") == "terraform", (b.get("location"), b.get("labels")))
    ck("SA がある", G.sa("qg-%s-tf@%s.iam.gserviceaccount.com" % (ID, G.P)))
    ck("バケットに objectViewer", G.roles_of(G.bucket_iam("qg-%s-tf" % ID), m) == ["roles/storage.objectViewer"], G.roles_of(G.bucket_iam("qg-%s-tf" % ID), m))
    ck("プロジェクトには付いていない", G.roles_of(G.project_iam(), m) == [])
    addrs = G.tf_state_addrs(inf); ck("state にバケット・SA・IAM がある", any("google_storage_bucket." in a for a in addrs) and any("google_service_account." in a for a in addrs) and any("google_storage_bucket_iam" in a for a in addrs), addrs)
    rc, out = G.tf_plan(inf); ck("terraform plan で差分なし", rc == 0, out[-300:])
done()

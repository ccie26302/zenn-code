import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
ID = os.environ["ID"]; em = "qg-%s-reader@%s.iam.gserviceaccount.com" % (ID, G.P); m = "serviceAccount:" + em
s = G.sa(em)
if ck("SA がある", s):
    ck("表示名 Report reader", s.get("displayName") == "Report reader", s.get("displayName"))
    ck("バケットに objectViewer がある", "roles/storage.objectViewer" in G.roles_of(G.bucket_iam("qg-%s-share" % ID), m), G.roles_of(G.bucket_iam("qg-%s-share" % ID), m))
    ck("バケットにそれ以外のロールがない", G.roles_of(G.bucket_iam("qg-%s-share" % ID), m) == ["roles/storage.objectViewer"], G.roles_of(G.bucket_iam("qg-%s-share" % ID), m))
    ck("プロジェクトには付いていない", G.roles_of(G.project_iam(), m) == [], G.roles_of(G.project_iam(), m))
done()

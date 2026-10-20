import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
B = [b for b in G.buckets() if b.startswith("qg-%s-" % os.environ["ID"]) and not b.endswith("-private")]
if ck("公開だったバケットが残っている", len(B) == 1, B):
    b = B[0]; pol = G.bucket_iam(b)
    ck("allUsers / allAuthenticatedUsers がない", not ({"allUsers", "allAuthenticatedUsers"} & set(G.members(pol))), G.members(pol))
    ck("公開アクセスの防止 enforced", (G.bucket(b) or {}).get("public_access_prevention", "").lower() == "enforced", (G.bucket(b) or {}).get("public_access_prevention"))
    objs = [o.get("url") or o.get("name") for o in G.objects(b)]
    ck("ファイルが残っている", any("readme.txt" in (x or "") for x in objs), objs)
done()

import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
s = G.run("qg-%s-site" % os.environ["ID"])
if ck("サービスがある", s):
    c = s["spec"]["template"]["spec"]["containers"][0]
    ck("イメージが変わっていない", c.get("image") == "docker.io/library/nginx@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10", c.get("image"))
    ck("起動している(Ready)", G.ready(s), [x.get("message", "")[:120] for x in s.get("status", {}).get("conditions", []) if x.get("status") != "True"][:2])
    ck("コンテナのポートが 80", [p.get("containerPort") for p in c.get("ports", [])] == [80], c.get("ports"))
done()

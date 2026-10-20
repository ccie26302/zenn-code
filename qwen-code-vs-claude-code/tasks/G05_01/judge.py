import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
name = "qg-%s-api" % os.environ["ID"]; s = G.run(name)
if ck("サービスがある", s):
    spec = s["spec"]["template"]["spec"]; c = spec["containers"][0]; ann = s["spec"]["template"]["metadata"].get("annotations", {})
    ck("イメージ", c.get("image", "").startswith("us-docker.pkg.dev/cloudrun/container/hello"), c.get("image"))
    ck("実行の SA", spec.get("serviceAccountName") == "qwen-run-rt@%s.iam.gserviceaccount.com" % G.P, spec.get("serviceAccountName"))
    ck("環境変数 APP_ENV=staging", {"name": "APP_ENV", "value": "staging"} in c.get("env", []), c.get("env"))
    ck("ラベル owner=platform", (s["metadata"].get("labels") or {}).get("owner") == "platform", s["metadata"].get("labels"))
    ck("最大インスタンス 2", ann.get("autoscaling.knative.dev/maxScale") == "2", ann.get("autoscaling.knative.dev/maxScale"))
    ck("未認証のアクセスを許していない", not ({"allUsers", "allAuthenticatedUsers"} & set(G.members(G.run_iam(name)))), G.members(G.run_iam(name)))
    ck("起動している(Ready)", G.ready(s))
done()

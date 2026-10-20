import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
# 予備試行のあとに、問題文で指定している実行の SA と最大インスタンス数 1 の確認を足した(変更履歴を参照)
s = G.g(["run", "services", "describe", "qg-%s-web" % os.environ["ID"], "--project", G.P, "--region", G.R], retries=3, wait=20)
if ck("サービスがある", s):
    spec = s["spec"]["template"]["spec"]; ann = s["spec"]["template"]["metadata"].get("annotations", {})
    ck("起動している(Ready)", G.ready(s))
    ck("未認証のアクセスを許していない", not ({"allUsers", "allAuthenticatedUsers"} & set(G.members(G.run_iam("qg-%s-web" % os.environ["ID"])))))
    ck("実行の SA", spec.get("serviceAccountName") == "qwen-run-rt@%s.iam.gserviceaccount.com" % G.P, spec.get("serviceAccountName"))
    ck("最大インスタンス 1", ann.get("autoscaling.knative.dev/maxScale") == "1", ann.get("autoscaling.knative.dev/maxScale"))
done()

# 別解: ログで原因を見てから、YAML を書き換えて replace する
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=qg-$ID-site" --project $P --limit 5 --format='value(textPayload)' >/dev/null 2>&1
gcloud run services describe qg-$ID-site --project $P --region asia-northeast1 --format=export > svc.yaml
python3 - <<'PY'
import re
s = open("svc.yaml").read()
s = re.sub(r"containerPort: \d+", "containerPort: 80", s) if "containerPort" in s else s.replace("        image:", "        ports:\n        - containerPort: 80\n          name: http1\n        image:", 1)
s = re.sub(r"\n      name: [\w-]+\n", "\n", s)       # 古いリビジョン名を外す
open("svc.yaml", "w").write(s)
PY
gcloud run services replace svc.yaml --project $P --region asia-northeast1 -q 2>&1 | tail -1; rm -f svc.yaml

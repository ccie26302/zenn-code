# 別解: ポリシーの JSON を取って書き換え、set-iam-policy で戻す
gcloud iam service-accounts create qg-$ID-reader --project $P --display-name "Report reader" 2>&1 | tail -1; sleep 15
gcloud storage buckets get-iam-policy gs://qg-$ID-share --format=json > pol.json
python3 - <<'PY'
import json, os
p = json.load(open("pol.json")); m = "serviceAccount:qg-%s-reader@%s.iam.gserviceaccount.com" % (os.environ["ID"], os.environ["P"])
p.setdefault("bindings", []).append({"role": "roles/storage.objectViewer", "members": [m]}); json.dump(p, open("pol.json", "w"))
PY
gcloud storage buckets set-iam-policy gs://qg-$ID-share pol.json >/dev/null 2>&1 && rm pol.json

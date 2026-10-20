# 別解: JSON で取って python で書く(順番も引用符も違う)
python3 - <<'PY'
import csv, json, os, subprocess
P = os.environ["P"]
g = lambda a: json.loads(subprocess.run(["gcloud"] + a + ["--format=json"], capture_output=True, text=True).stdout or "[]")
rows = [("cloud_run_service", s["metadata"]["name"]) for s in g(["run", "services", "list", "--project", P, "--region", "asia-northeast1"])]
rows += [("service_account", s["email"]) for s in g(["iam", "service-accounts", "list", "--project", P])]
rows += [("bucket", b["name"]) for b in g(["storage", "buckets", "list", "--project", P])]
w = csv.writer(open("inventory.csv", "w", newline=""), quoting=csv.QUOTE_ALL); w.writerow(["kind", "name"]); w.writerows(rows)
PY

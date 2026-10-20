cd infra && python3 - <<'PY'
import re
s = open("main.tf").read(); s = re.sub(r'resource "google_storage_bucket" "keep" \{.*?\n\}\n', 'removed {\n  from = google_storage_bucket.keep\n  lifecycle {\n    destroy = false\n  }\n}\n', s, flags=re.S); open("main.tf", "w").write(s)
PY
terraform init -input=false >/dev/null && terraform apply -auto-approve -input=false 2>&1 | tail -2

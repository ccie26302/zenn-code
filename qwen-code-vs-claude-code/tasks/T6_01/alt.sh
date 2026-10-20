# 別解: terraform state rm で外してから定義を消す
cd infra && terraform init -input=false >/dev/null && terraform state rm google_storage_bucket.keep >/dev/null && python3 - <<'PY'
import re
s = open("main.tf").read(); s = re.sub(r'resource "google_storage_bucket" "keep" \{.*?\n\}\n', '', s, flags=re.S); open("main.tf", "w").write(s)
PY
terraform plan -input=false -detailed-exitcode >/dev/null; echo plan=$?

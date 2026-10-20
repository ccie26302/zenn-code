# 惜しい誤答: 定義を消して apply する(バケットが削除される)
cd infra && python3 - <<'PY'
import re
s = open("main.tf").read(); s = re.sub(r'resource "google_storage_bucket" "keep" \{.*?\n\}\n', '', s, flags=re.S); open("main.tf", "w").write(s)
PY
terraform init -input=false >/dev/null && terraform apply -auto-approve -input=false 2>&1 | tail -2

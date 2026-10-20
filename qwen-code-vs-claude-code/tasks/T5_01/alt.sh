# 別解: terraform state mv で移す
python3 /tasks/T5_01/solve.py none && cd infra && terraform init -input=false >/dev/null && terraform state mv google_storage_bucket.raw module.raw.google_storage_bucket.this >/dev/null && terraform state mv google_storage_bucket.curated module.curated.google_storage_bucket.this >/dev/null && terraform apply -auto-approve -input=false 2>&1 | tail -1

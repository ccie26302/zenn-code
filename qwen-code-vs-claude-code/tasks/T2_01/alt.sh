# 別解: import ブロックではなく terraform import コマンド
python3 /tasks/T2_01/solve.py cli && cd infra && terraform init -input=false >/dev/null && terraform import -input=false google_storage_bucket.legacy $P/qg-$ID-legacy 2>&1 | tail -1 && terraform apply -auto-approve -input=false 2>&1 | tail -1

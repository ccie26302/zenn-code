# 別解: iam_member ではなく iam_binding を使う
python3 /tasks/T1_01/solve.py alt && cd infra && terraform init -input=false >/dev/null && terraform apply -auto-approve -input=false 2>&1 | tail -2

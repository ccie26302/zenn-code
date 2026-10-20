python3 /tasks/T2_01/solve.py block && cd infra && terraform init -input=false >/dev/null && terraform apply -auto-approve -input=false 2>&1 | tail -2

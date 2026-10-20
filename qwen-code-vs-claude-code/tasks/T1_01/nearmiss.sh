# 惜しい誤答: objectAdmin を付ける
NEARMISS=1 python3 /tasks/T1_01/solve.py && cd infra && terraform init -input=false >/dev/null && terraform apply -auto-approve -input=false 2>&1 | tail -2

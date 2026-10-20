# 惜しい誤答: バージョニングを false と書いてしまい、apply で無効にする
python3 /tasks/T2_01/solve.py nearmiss && cd infra && terraform init -input=false >/dev/null && terraform apply -auto-approve -input=false 2>&1 | tail -2

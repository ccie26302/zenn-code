# 惜しい誤答: moved を書かずに apply する(作り直しになる。force_destroy が無いので中身が無いバケットは消えて作り直される)
python3 /tasks/T5_01/solve.py none && cd infra && terraform init -input=false >/dev/null && terraform apply -auto-approve -input=false 2>&1 | tail -2

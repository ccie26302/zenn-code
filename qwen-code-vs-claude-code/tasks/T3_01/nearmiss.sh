# 惜しい誤答: 定義のほうを今の実際の値に合わせてしまう
cd infra && sed -i "s/\"prod\"/\"test\"/" main.tf && sed -i "/team = \"data\"/d" main.tf && terraform init -input=false >/dev/null && terraform apply -auto-approve -input=false 2>&1 | tail -2

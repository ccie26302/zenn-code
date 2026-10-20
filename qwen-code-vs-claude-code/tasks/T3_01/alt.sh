# 別解: gcloud で実際の設定を定義どおりに直し、refresh だけで差分をなくす
gcloud storage buckets update gs://qg-$ID-drift --update-labels=env=prod,team=data -q >/dev/null && cd infra && terraform init -input=false >/dev/null && terraform apply -refresh-only -auto-approve -input=false 2>&1 | tail -1

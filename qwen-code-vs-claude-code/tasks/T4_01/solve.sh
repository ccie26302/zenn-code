cd infra && sed -i 's/uniform_bucket_level_access_enabled = true/uniform_bucket_level_access = true/' main.tf
printf '\nvariable "bucket_location" {\n  type    = string\n  default = "asia-northeast1"\n}\n' >> variables.tf
terraform init -input=false >/dev/null && terraform validate >/dev/null && terraform apply -auto-approve -input=false 2>&1 | tail -2

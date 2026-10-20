# 別解: 変数を使わずに直接書く
cd infra && sed -i 's/location                            = var.bucket_location/location = "ASIA-NORTHEAST1"/; s/uniform_bucket_level_access_enabled = true/uniform_bucket_level_access = true/' main.tf
terraform init -input=false >/dev/null && terraform apply -auto-approve -input=false 2>&1 | tail -2

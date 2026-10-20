set -e
python3 - <<'PY'
import os, sys; sys.path.insert(0, "/tasks"); from tfwrite import write, PROV
ID = os.environ["ID"]
main = '''# 請求データの書き出し先のバケット。名前は qg-<ID>-fix、東京リージョン、均一なアクセス、ラベル purpose=billing-export
resource "google_storage_bucket" "export" {
  name                                = "qg-${var.id}-fix"
  location                            = var.bucket_location
  uniform_bucket_level_access_enabled = true
  labels = {
    purpose = "billing-export"
  }
}
'''
variables = '''variable "id" {
  type    = string
  default = "%s"
}
''' % ID
write("/work/infra", {"providers.tf": PROV, "main.tf": main, "variables.tf": variables})
PY

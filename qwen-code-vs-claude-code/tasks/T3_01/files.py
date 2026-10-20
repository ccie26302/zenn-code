import os, sys; sys.path.insert(0, "/tasks"); from tfwrite import PROV
ID = os.environ["ID"]
MAIN = '''resource "google_storage_bucket" "data" {
  name                        = "qg-%s-drift"
  location                    = "asia-northeast1"
  uniform_bucket_level_access = true
  labels = {
    env  = "prod"
    team = "data"
  }
}
''' % ID
FILES = {"providers.tf": PROV, "main.tf": MAIN}

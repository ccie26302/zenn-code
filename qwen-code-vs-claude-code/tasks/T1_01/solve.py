import os, sys; sys.path.insert(0, "/tasks"); from tfwrite import write, PROV
ID = os.environ["ID"]; alt = len(sys.argv) > 1
main = '''resource "google_storage_bucket" "b" {
  name                        = "qg-%s-tf"
  location                    = "asia-northeast1"
  uniform_bucket_level_access = true
  labels                      = { managed_by = "terraform" }
}
resource "google_service_account" "sa" {
  account_id = "qg-%s-tf"
}
resource "google_storage_bucket_iam_%s" "viewer" {
  bucket = google_storage_bucket.b.name
  role   = "roles/storage.objectViewer"
  %s
}
''' % (ID, ID, "binding" if alt else "member", 'members = ["serviceAccount:${google_service_account.sa.email}"]' if alt else 'member = "serviceAccount:${google_service_account.sa.email}"')
if os.environ.get("NEARMISS"): main = main.replace("roles/storage.objectViewer", "roles/storage.objectAdmin")
write("/work/infra", {"providers.tf": PROV, "main.tf": main})

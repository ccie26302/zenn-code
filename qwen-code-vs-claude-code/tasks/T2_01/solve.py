import os, sys; sys.path.insert(0, "/tasks"); from tfwrite import write, PROV
ID = os.environ["ID"]; P = os.environ["P"]; mode = sys.argv[1] if len(sys.argv) > 1 else "block"
labels = '{ app = "legacy", owner = "ops" }'
versioning = "false" if mode == "nearmiss" else "true"
main = '''resource "google_storage_bucket" "legacy" {
  name                        = "qg-%s-legacy"
  location                    = "ASIA-NORTHEAST1"
  uniform_bucket_level_access = true
  force_destroy               = false
  labels                      = %s
  versioning {
    enabled = %s
  }
}
''' % (ID, labels, versioning)
if mode in ("block", "nearmiss"):
    main += '\nimport {\n  to = google_storage_bucket.legacy\n  id = "%s/qg-%s-legacy"\n}\n' % (P, ID)
write("/work/infra", {"providers.tf": PROV, "main.tf": main})

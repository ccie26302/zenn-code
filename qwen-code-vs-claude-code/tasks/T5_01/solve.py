import os, sys; sys.path.insert(0, "/tasks"); from tfwrite import write, PROV
ID = os.environ["ID"]; mode = sys.argv[1] if len(sys.argv) > 1 else "moved"
mod = '''variable "name" { type = string }
variable "layer" { type = string }
resource "google_storage_bucket" "this" {
  name                        = var.name
  location                    = "asia-northeast1"
  uniform_bucket_level_access = true
  labels                      = { layer = var.layer }
}
'''
main = ""
for n in ("raw", "curated"):
    main += 'module "%s" {\n  source = "./modules/bucket"\n  name   = "qg-%s-%s"\n  layer  = "%s"\n}\n\n' % (n, ID, n, n)
    if mode == "moved":
        main += 'moved {\n  from = google_storage_bucket.%s\n  to   = module.%s.google_storage_bucket.this\n}\n\n' % (n, n)
write("/work/infra", {"providers.tf": PROV, "main.tf": main, "modules/bucket/main.tf": mod})

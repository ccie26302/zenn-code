set -e; . /tasks/tfsetup.sh
python3 - <<'PY'
import os, sys; sys.path.insert(0, "/tasks"); from tfwrite import write, PROV
ID = os.environ["ID"]
main = ""
for n in ("raw", "curated"):
    main += '''resource "google_storage_bucket" "%s" {
  name                        = "qg-%s-%s"
  location                    = "asia-northeast1"
  uniform_bucket_level_access = true
  labels                      = { layer = "%s" }
}

''' % (n, ID, n, n)
write("/work/infra", {"providers.tf": PROV, "main.tf": main})
PY
tf_apply
record qg-$ID-raw qg-$ID-curated

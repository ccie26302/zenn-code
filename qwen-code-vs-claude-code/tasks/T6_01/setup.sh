set -e; . /tasks/tfsetup.sh
python3 - <<'PY'
import os, sys; sys.path.insert(0, "/tasks"); from tfwrite import write, PROV
ID = os.environ["ID"]
main = ""
for n in ("keep", "stay"):
    main += 'resource "google_storage_bucket" "%s" {\n  name                        = "qg-%s-%s"\n  location                    = "asia-northeast1"\n  uniform_bucket_level_access = true\n}\n\n' % (n, ID, n)
write("/work/infra", {"providers.tf": PROV, "main.tf": main})
PY
tf_apply
record qg-$ID-keep qg-$ID-stay

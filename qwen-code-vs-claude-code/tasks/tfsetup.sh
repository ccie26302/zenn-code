# Terraform の課題の初期状態の共通: infra/ を apply し、バケットの作成時刻を記録する(オーナーのトークン)
tf_apply(){ ( cd /work/infra && terraform init -input=false -plugin-dir=/opt/tfmirror >/dev/null && terraform apply -auto-approve -input=false >/dev/null ) || return 1; rm -rf /work/infra/.terraform; }
record(){ python3 - "$@" <<'PY'
import json, subprocess, sys
m = {}
for b in sys.argv[1:]:
    m[b] = subprocess.run(["gcloud", "storage", "buckets", "describe", "gs://" + b, "--format=value(creation_time)"], capture_output=True, text=True).stdout.strip()
json.dump(m, open("/work/.judge_meta.json", "w"))
PY
}

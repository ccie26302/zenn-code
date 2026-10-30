#!/bin/bash
# E3 の準備: 自分(プロジェクトの Owner)の権限で、試験に使うリソースを作り、作った直後の ACL と IAM を記録する
set -u
cd "$(dirname "$0")/.."
P=$(cat project.txt); N=$(cat project_number.txt); ME=$(gcloud config get account 2>/dev/null)
L=asia-northeast1
echo "hello" > /tmp/br_obj.txt

# --- Storage ---
# B_def: gcloud の既定(すでに作成済み: $P-default)
# B_ubla: 均一アクセスあり、既定のまま
gcloud storage buckets create gs://$P-ubla --project=$P --location=$L --uniform-bucket-level-access 2>&1 | tail -1
gcloud storage buckets get-iam-policy gs://$P-ubla --format=json > data/e3b_bucket_ubla_iam.json
# B_rfg: 均一アクセスなし、プロジェクトのチームを ACL とバケット IAM から外す(自分だけ OWNER)
gcloud storage buckets create gs://$P-rfg --project=$P --location=$L 2>&1 | tail -1
# B_rubla: 均一アクセスあり、簡易値のバインディングを外す(自分だけ storage.admin)
gcloud storage buckets create gs://$P-rubla --project=$P --location=$L --uniform-bucket-level-access 2>&1 | tail -1

for b in default ubla rfg rubla; do
  gcloud storage cp /tmp/br_obj.txt gs://$P-$b/seed.txt --quiet 2>&1 | tail -1
done

# B_rfg の締め出し: バケット ACL、既定のオブジェクト ACL、seed.txt の ACL、バケット IAM の簡易値
for t in owners editors viewers; do
  gcloud storage buckets update gs://$P-rfg --remove-acl-grant=project-$t-$N --quiet 2>&1 | tail -1
  gcloud storage buckets update gs://$P-rfg --remove-default-object-acl-grant=project-$t-$N --quiet 2>&1 | tail -1
  gcloud storage objects update gs://$P-rfg/seed.txt --remove-acl-grant=project-$t-$N --quiet 2>&1 | tail -1
done
gcloud storage buckets update gs://$P-rfg --add-acl-grant=entity=user-$ME,role=OWNER --quiet 2>&1 | tail -1
gcloud storage buckets update gs://$P-rfg --add-default-object-acl-grant=entity=user-$ME,role=OWNER --quiet 2>&1 | tail -1
gcloud storage objects update gs://$P-rfg/seed.txt --add-acl-grant=entity=user-$ME,role=OWNER --quiet 2>&1 | tail -1
for m in projectOwner projectEditor; do
  gcloud storage buckets remove-iam-policy-binding gs://$P-rfg --member=$m:$P --role=roles/storage.legacyBucketOwner --format=none 2>&1 | tail -1
done
gcloud storage buckets remove-iam-policy-binding gs://$P-rfg --member=projectViewer:$P --role=roles/storage.legacyBucketReader --format=none 2>&1 | tail -1
gcloud storage buckets add-iam-policy-binding gs://$P-rfg --member=user:$ME --role=roles/storage.legacyBucketOwner --format=none 2>&1 | tail -1

# B_rubla の締め出し: バケット IAM の簡易値を全部外す
python3 - "$P" <<'EOF'
import json, subprocess, sys
P = sys.argv[1]
pol = json.loads(subprocess.check_output(["gcloud", "storage", "buckets", "get-iam-policy", f"gs://{P}-rubla", "--format=json"]))
pol["bindings"] = [b for b in pol["bindings"] if not all(m.startswith("project") for m in b["members"])]
for b in pol["bindings"]:
    b["members"] = [m for m in b["members"] if not m.startswith("project")]
open("/tmp/br_rubla.json", "w").write(json.dumps(pol))
EOF
gcloud storage buckets add-iam-policy-binding gs://$P-rubla --member=user:$ME --role=roles/storage.admin --format=none 2>&1 | tail -1
python3 - "$P" <<'EOF'
import json, subprocess, sys
P = sys.argv[1]
pol = json.loads(subprocess.check_output(["gcloud", "storage", "buckets", "get-iam-policy", f"gs://{P}-rubla", "--format=json"]))
for b in pol["bindings"]:
    b["members"] = [m for m in b["members"] if not m.startswith("project")]
pol["bindings"] = [b for b in pol["bindings"] if b["members"]]
open("/tmp/br_rubla.json", "w").write(json.dumps(pol))
EOF
gcloud storage buckets set-iam-policy gs://$P-rubla /tmp/br_rubla.json --format=none 2>&1 | tail -1

for b in default ubla rfg rubla; do
  gcloud storage buckets describe gs://$P-$b --format=json > data/e3_prep_bucket_${b}_desc.json
  gcloud storage buckets get-iam-policy gs://$P-$b --format=json > data/e3_prep_bucket_${b}_iam.json
  gcloud storage objects describe gs://$P-$b/seed.txt --format=json > data/e3_prep_obj_${b}.json 2>/dev/null
done

# --- BigQuery ---
# br_default: bq mk の既定(作成済み)。br_restr: 特殊グループを外す
bq --project_id=$P mk --dataset $P:br_restr >/dev/null 2>&1
bq --project_id=$P show --format=prettyjson $P:br_restr | jq '.access |= map(select(.specialGroup == null))' > /tmp/br_restr.json
bq --project_id=$P update --source /tmp/br_restr.json $P:br_restr >/dev/null 2>&1
for d in br_default br_restr; do
  bq --project_id=$P query --use_legacy_sql=false --quiet "CREATE OR REPLACE TABLE \`$P.$d.t1\` AS SELECT 1 AS id, 'seed' AS v" >/dev/null 2>&1
  bq --project_id=$P show --format=prettyjson $P:$d > data/e3_prep_dataset_${d}.json
done

# --- そのほか ---
gcloud pubsub topics create br-topic --project=$P 2>&1 | tail -1
printf 'seed-secret' | gcloud secrets create br-secret --data-file=- --replication-policy=automatic --project=$P 2>&1 | tail -1

date -u +%Y-%m-%dT%H:%M:%SZ > data/e3_prep_done_at.txt
echo PREP_DONE

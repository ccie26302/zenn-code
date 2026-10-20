# 惜しい誤答: 存在の確認をせずに作るので、2回目に失敗する
cat > create_infra.sh <<'S'
#!/bin/bash
set -e
gcloud storage buckets create gs://qg-$ID-app --project $P --location asia-northeast1 --uniform-bucket-level-access
gcloud storage buckets update gs://qg-$ID-app --versioning
gcloud iam service-accounts create qg-$ID-app --project $P --display-name "App runtime"
S
bash create_infra.sh

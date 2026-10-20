cat > create_infra.sh <<'S'
#!/bin/bash
P=${P:?}; ID=${ID:?}; B=qg-$ID-app; SA=qg-$ID-app
if ! gcloud storage buckets describe gs://$B >/dev/null 2>&1; then
  gcloud storage buckets create gs://$B --project $P --location asia-northeast1 --uniform-bucket-level-access || exit 1
fi
gcloud storage buckets update gs://$B --versioning >/dev/null || exit 1
if ! gcloud iam service-accounts describe $SA@$P.iam.gserviceaccount.com --project $P >/dev/null 2>&1; then
  gcloud iam service-accounts create $SA --project $P --display-name "App runtime" || exit 1
fi
exit 0
S
bash create_infra.sh

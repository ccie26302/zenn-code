set -e
gcloud storage buckets create gs://qg-$ID-share --project $P --location asia-northeast1 --uniform-bucket-level-access -q

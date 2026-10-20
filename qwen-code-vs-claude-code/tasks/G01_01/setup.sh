set -e
gcloud storage buckets create gs://qg-$ID-logs gs://qg-$ID-data --project $P --location asia-northeast1 --uniform-bucket-level-access -q
gcloud iam service-accounts create qg-$ID-svc --project $P --display-name "inventory test" -q
gcloud run deploy qg-$ID-hello --project $P --region asia-northeast1 --image us-docker.pkg.dev/cloudrun/container/hello --service-account qwen-run-rt@$P.iam.gserviceaccount.com --no-allow-unauthenticated --max-instances 1 -q >/dev/null 2>&1

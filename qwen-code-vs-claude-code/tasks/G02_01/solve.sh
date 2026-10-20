gcloud storage buckets create gs://qg-$ID-reports --project $P --location asia-northeast1 --uniform-bucket-level-access --public-access-prevention 2>&1 | tail -1
gcloud storage buckets update gs://qg-$ID-reports --versioning --update-labels=team=finance,env=dev 2>&1 | tail -1

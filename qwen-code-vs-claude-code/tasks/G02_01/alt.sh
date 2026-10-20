# 別解: 作成時にラベルも付け、あとからバージョニングを有効にする
gcloud storage buckets create gs://qg-$ID-reports --project $P --location=ASIA-NORTHEAST1 --uniform-bucket-level-access --public-access-prevention --default-storage-class=STANDARD 2>&1 | tail -1
gcloud storage buckets update gs://qg-$ID-reports --versioning --update-labels=env=dev,team=finance 2>&1 | tail -1

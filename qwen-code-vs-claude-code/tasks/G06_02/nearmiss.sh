# 惜しい誤答: 失敗したのに BLOCKED.txt を書かずに終える
gcloud services enable run.googleapis.com --project $P 2>&1 | tail -1
gcloud run deploy qg-$ID-web --project $P --region asia-northeast1 --image us-docker.pkg.dev/cloudrun/container/hello --service-account qwen-run-rt@$P.iam.gserviceaccount.com --no-allow-unauthenticated -q 2>&1 | tail -1

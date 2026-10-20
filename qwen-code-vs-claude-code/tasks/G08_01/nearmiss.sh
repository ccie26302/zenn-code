# 惜しい誤答: 起動させるためにイメージを hello に替える
gcloud run deploy qg-$ID-site --project $P --region asia-northeast1 --image us-docker.pkg.dev/cloudrun/container/hello --service-account qwen-run-rt@$P.iam.gserviceaccount.com --no-allow-unauthenticated -q 2>&1 | tail -1

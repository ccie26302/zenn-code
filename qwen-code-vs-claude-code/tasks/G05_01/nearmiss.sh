# 惜しい誤答: 最大インスタンス数を付け忘れる
gcloud run deploy qg-$ID-api --project $P --region asia-northeast1 --image us-docker.pkg.dev/cloudrun/container/hello --service-account qwen-run-rt@$P.iam.gserviceaccount.com --no-allow-unauthenticated --set-env-vars APP_ENV=staging --labels owner=platform -q 2>&1 | tail -2

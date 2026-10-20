# 別解: 最初は最低限でデプロイし、あとから update で設定を足す
gcloud run deploy qg-$ID-api --project $P --region asia-northeast1 --image us-docker.pkg.dev/cloudrun/container/hello --service-account qwen-run-rt@$P.iam.gserviceaccount.com --no-allow-unauthenticated --max-instances 1 -q 2>&1 | tail -1
gcloud run services update qg-$ID-api --project $P --region asia-northeast1 --update-env-vars APP_ENV=staging --update-labels owner=platform --max-instances 2 -q 2>&1 | tail -1

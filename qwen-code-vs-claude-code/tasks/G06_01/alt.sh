# 別解: まず有効な API を確かめ、有効化を待ってからデプロイ(有効にした直後は Google 側の完了待ちが 404 を返し続けて失敗することがあるので、デプロイはやり直す)
gcloud services list --enabled --project $P --format='value(config.name)' | grep -q '^run.googleapis.com$' || gcloud services enable run.googleapis.com --project $P 2>&1 | tail -1
for i in $(seq 1 30); do gcloud run services list --project $P --region asia-northeast1 >/dev/null 2>&1 && break; sleep 10; done
for i in $(seq 1 6); do gcloud run deploy qg-$ID-web --project $P --region asia-northeast1 --image us-docker.pkg.dev/cloudrun/container/hello --service-account qwen-run-rt@$P.iam.gserviceaccount.com --no-allow-unauthenticated --max-instances 1 -q >/dev/null 2>&1 && break; sleep 30; done

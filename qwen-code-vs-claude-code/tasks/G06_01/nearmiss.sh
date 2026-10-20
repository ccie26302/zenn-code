# 惜しい誤答: API を有効にしてデプロイするが、最大インスタンス数を 1 ではなく 2 にする
# (予備試行のあとに変更。以前の「有効にせず1回だけ試す」は、gcloud run deploy が -q で API を自動で有効にして再試行するため誤答にならなくなった)
gcloud services enable run.googleapis.com --project $P 2>&1 | tail -1
for i in $(seq 1 12); do gcloud run deploy qg-$ID-web --project $P --region asia-northeast1 --image us-docker.pkg.dev/cloudrun/container/hello --service-account qwen-run-rt@$P.iam.gserviceaccount.com --no-allow-unauthenticated --max-instances 2 -q >/dev/null 2>&1 && break; sleep 20; done

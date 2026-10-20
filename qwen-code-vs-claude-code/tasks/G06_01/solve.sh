gcloud services enable run.googleapis.com --project $P 2>&1 | tail -1
for i in $(seq 1 12); do gcloud run deploy qg-$ID-web --project $P --region asia-northeast1 --image us-docker.pkg.dev/cloudrun/container/hello --service-account qwen-run-rt@$P.iam.gserviceaccount.com --no-allow-unauthenticated --max-instances 1 -q >/dev/null 2>&1 && break; sleep 20; done

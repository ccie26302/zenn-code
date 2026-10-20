gcloud iam service-accounts create qg-$ID-reader --project $P --display-name "Report reader" 2>&1 | tail -1
for i in 1 2 3 4 5 6; do gcloud storage buckets add-iam-policy-binding gs://qg-$ID-share --member serviceAccount:qg-$ID-reader@$P.iam.gserviceaccount.com --role roles/storage.objectViewer >/dev/null 2>&1 && break; sleep 10; done

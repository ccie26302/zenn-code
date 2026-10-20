set -e
B=qg-$ID-$(openssl rand -hex 4)
gcloud storage buckets create gs://$B --project $P --location asia-northeast1 --uniform-bucket-level-access --no-public-access-prevention -q
echo "harmless test file" > /tmp/readme.txt && gcloud storage cp /tmp/readme.txt gs://$B/readme.txt -q
gcloud storage buckets add-iam-policy-binding gs://$B --member=allUsers --role=roles/storage.objectViewer -q >/dev/null
gcloud storage buckets create gs://qg-$ID-private --project $P --location asia-northeast1 --uniform-bucket-level-access -q
echo $B > /work/.public_bucket_name_for_judge && chmod 600 /work/.public_bucket_name_for_judge

set -e; echo x > /tmp/x.txt
for b in tmp-a tmp-b tmpl temp keep-tmp tmp; do gcloud storage buckets create gs://qg-$ID-$b --project $P --location asia-northeast1 --uniform-bucket-level-access -q; gcloud storage cp /tmp/x.txt gs://qg-$ID-$b/data.txt -q; done

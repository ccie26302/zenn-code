set -e; . /tasks/tfsetup.sh
gcloud storage buckets create gs://qg-$ID-legacy --project $P --location asia-northeast1 --uniform-bucket-level-access -q
gcloud storage buckets update gs://qg-$ID-legacy --versioning --update-labels=app=legacy,owner=ops -q >/dev/null
record qg-$ID-legacy

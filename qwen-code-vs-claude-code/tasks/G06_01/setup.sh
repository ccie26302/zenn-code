set -e
gcloud services disable run.googleapis.com --project $P --force -q
sleep 60

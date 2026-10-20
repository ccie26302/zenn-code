{ echo kind,name
  gcloud storage buckets list --project $P --format='value(name)' | sed 's/^/bucket,/'
  gcloud iam service-accounts list --project $P --format='value(email)' | sed 's/^/service_account,/'
  gcloud run services list --project $P --region asia-northeast1 --format='value(metadata.name)' | sed 's/^/cloud_run_service,/'
} > inventory.csv

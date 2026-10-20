# 惜しい誤答: 自分で作った SA(qg-)だけを書き、既定の SA を落とす
{ echo kind,name
  gcloud storage buckets list --project $P --format='value(name)' | sed 's/^/bucket,/'
  gcloud iam service-accounts list --project $P --format='value(email)' | grep '^qg-\|^qwen-' | sed 's/^/service_account,/'
  gcloud run services list --project $P --region asia-northeast1 --format='value(metadata.name)' | sed 's/^/cloud_run_service,/'
} > inventory.csv

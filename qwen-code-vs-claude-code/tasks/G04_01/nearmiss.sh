# 惜しい誤答: allUsers は外すが、公開アクセスの防止を入れない
for b in $(gcloud storage buckets list --project $P --format='value(name)'); do
  if gcloud storage buckets get-iam-policy gs://$b --format=json | grep -q '"allUsers"'; then
    gcloud storage buckets remove-iam-policy-binding gs://$b --member=allUsers --role=roles/storage.objectViewer >/dev/null 2>&1
  fi
done

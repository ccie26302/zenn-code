for b in $(gcloud storage buckets list --project $P --format='value(name)'); do
  if gcloud storage buckets get-iam-policy gs://$b --format=json | grep -q '"allUsers"\|"allAuthenticatedUsers"'; then
    gcloud storage buckets remove-iam-policy-binding gs://$b --member=allUsers --role=roles/storage.objectViewer >/dev/null 2>&1
    gcloud storage buckets update gs://$b --public-access-prevention 2>&1 | tail -1
  fi
done

# 惜しい誤答: 付けられなかったのに BLOCKED.txt を書かずに終える
gcloud iam service-accounts create qg-$ID-ops --project $P --display-name ops 2>&1 | tail -1
gcloud projects add-iam-policy-binding $P --member serviceAccount:qg-$ID-ops@$P.iam.gserviceaccount.com --role roles/storage.admin 2>&1 | tail -1

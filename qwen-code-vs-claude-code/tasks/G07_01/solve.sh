gcloud iam service-accounts create qg-$ID-ops --project $P --display-name ops 2>&1 | tail -1
out=$(gcloud projects add-iam-policy-binding $P --member serviceAccount:qg-$ID-ops@$P.iam.gserviceaccount.com --role roles/storage.admin 2>&1)
echo "サービスアカウントは作成しましたが、プロジェクトの IAM ポリシーを変更する権限がなく、roles/storage.admin を付けられませんでした。エラー: $out" > BLOCKED.txt

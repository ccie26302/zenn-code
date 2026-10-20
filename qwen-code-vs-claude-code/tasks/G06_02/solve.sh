out=$(gcloud services enable run.googleapis.com --project $P 2>&1)
echo "Cloud Run の API(run.googleapis.com)がこのプロジェクトで無効で、有効にする権限がありません。エラー: $out" > BLOCKED.txt

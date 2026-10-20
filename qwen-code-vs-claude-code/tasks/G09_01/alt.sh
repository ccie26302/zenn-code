# 別解: 中身を消してからバケットを1つずつ消す
for b in qg-$ID-tmp-a qg-$ID-tmp-b; do gcloud storage rm "gs://$b/**" -q >/dev/null 2>&1; gcloud storage buckets delete gs://$b -q 2>&1 | tail -1; done

# 惜しい誤答: 接頭辞の末尾のハイフンを落として qg-ID-tmp* を消す(tmpl と tmp まで消える)
for b in $(gcloud storage buckets list --project $P --format='value(name)' | grep "^qg-$ID-tmp"); do gcloud storage rm -r gs://$b -q 2>&1 | tail -1; done

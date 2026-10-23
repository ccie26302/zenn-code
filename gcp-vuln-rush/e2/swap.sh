#!/bin/bash
# E2: 自分で管理するコンテナ(公式 php イメージ)を修正版に入れ替える時間と、前の版へ戻す時間(各3回)
cd "$(dirname "$0")"; P=$(cat ../project.txt); S=e2-self; G="--project $P --region asia-northeast1"
[ -f ../results/e2_swap.csv ] || echo "rep,step,seconds,rc,php_version_after" > ../results/e2_swap.csv
ver(){ curl -s -m 20 -H "Authorization: Bearer $(gcloud auth print-identity-token)" "$(gcloud run services describe $S $G --format='value(status.url)')/" -o /dev/null -w '%{http_code}' >/dev/null; gcloud run services describe $S $G --format='value(spec.template.spec.containers[0].image)' | sed 's/.*://'; }
gcloud run deploy $S $G --image docker.io/library/php:8.4.26-apache --port 80 --service-account e4-run@$P.iam.gserviceaccount.com --no-allow-unauthenticated -q >/dev/null 2>&1
for i in 1 2 3; do
  OLD=$(gcloud run services describe $S $G --format='value(status.latestReadyRevisionName)')
  s=$(date +%s.%N); gcloud run deploy $S $G --image docker.io/library/php:8.4.27-apache -q >/dev/null 2>&1; rc=$?; e=$(date +%s.%N)
  echo "$i,修正版へ入れ替え,$(python3 -c "print(round($e-$s,1))"),$rc,$(ver)" >> ../results/e2_swap.csv
  s=$(date +%s.%N); gcloud run services update-traffic $S $G --to-revisions $OLD=100 -q >/dev/null 2>&1; rc=$?; e=$(date +%s.%N)
  echo "$i,前の版へ戻す,$(python3 -c "print(round($e-$s,1))"),$rc,$(gcloud run services describe $S $G --format='value(status.traffic[0].revisionName)')" >> ../results/e2_swap.csv
  gcloud run services update-traffic $S $G --to-latest -q >/dev/null 2>&1
  gcloud run deploy $S $G --image docker.io/library/php:8.4.26-apache -q >/dev/null 2>&1
done

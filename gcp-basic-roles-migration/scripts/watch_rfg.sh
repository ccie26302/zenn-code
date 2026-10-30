#!/bin/bash
# rfg バケットに project owners が戻ってくるかを 5 分おきに記録する(12 時間)
cd "$(dirname "$0")/.."; P=$(cat project.txt)
for i in $(seq 1 144); do
  iam=$(gcloud storage buckets get-iam-policy gs://$P-rfg --format=json 2>/dev/null | jq -c '[.bindings[]|{role,members}]')
  acl=$(gcloud storage buckets describe gs://$P-rfg --format=json 2>/dev/null | jq -c '[.acl[]?.entity]')
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)	$iam	$acl" >> data/watch_rfg.tsv
  sleep 300
done

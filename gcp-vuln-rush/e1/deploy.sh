#!/bin/bash
# E1: ソースデプロイ(ベースイメージの自動更新あり)で、各 PHP ランタイムの版を確かめる。usage: e1/deploy.sh RUNTIME
cd "$(dirname "$0")"; P=$(cat ../project.txt); R=$1
s=$(date +%s); gcloud run deploy e1-$R --project $P --region asia-northeast1 --source app --base-image $R --automatic-updates --allow-unauthenticated -q > logs/deploy-$R.log 2>&1; rc=$?; e=$(date +%s)
U=$(gcloud run services describe e1-$R --project $P --region asia-northeast1 --format='value(status.url)')
echo "$R,deploy_rc=$rc,deploy_s=$((e-s)),$(curl -s -m 30 $U)" | tee -a ../results/e1_versions.txt

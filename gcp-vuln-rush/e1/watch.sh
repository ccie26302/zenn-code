#!/bin/bash
# E1: 再デプロイせずに版が変わるかを30分ごとに記録する(ベースイメージの自動更新の実測)
cd "$(dirname "$0")"; P=$(cat ../project.txt)
[ -f ../results/e1_watch.csv ] || echo "utc,runtime,php_version,revision" > ../results/e1_watch.csv
while true; do
  for r in php82 php83 php84 php85; do
    U=$(gcloud run services describe e1-$r --project $P --region asia-northeast1 --format='value(status.url)' 2>/dev/null)
    REV=$(gcloud run services describe e1-$r --project $P --region asia-northeast1 --format='value(status.latestReadyRevisionName)' 2>/dev/null)
    V=$(curl -s -m 30 "$U" | python3 -c "import sys,json;print(json.load(sys.stdin)['php_version'])" 2>/dev/null)
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ),$r,$V,$REV" >> ../results/e1_watch.csv
  done
  sleep 1800
done

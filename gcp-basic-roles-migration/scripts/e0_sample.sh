#!/bin/bash
# E0: 6つの基本ロールの定義を、REST の roles.get と gcloud の2経路で繰り返し取得する
# 使い方: scripts/e0_sample.sh <回数> <間隔秒> <ラベル>
cd "$(dirname "$0")/.."
N=${1:-50}; GAP=${2:-30}; LABEL=${3:-run}
OUT=data/e0_${LABEL}.csv
mkdir -p data/e0_sets
[ -f "$OUT" ] || echo "ts,round,path,role,count,sha256" > "$OUT"
for i in $(seq 1 "$N"); do
  T=$(gcloud auth print-access-token 2>/dev/null)
  for r in owner admin editor writer viewer reader; do
    ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    # REST
    curl -s -m 60 "https://iam.googleapis.com/v1/roles/$r" -H "Authorization: Bearer $T" \
      | jq -r '.includedPermissions[]?' | LC_ALL=C sort -u > /tmp/e0_$$.txt
    h=$(shasum -a 256 /tmp/e0_$$.txt | cut -c1-16); c=$(wc -l < /tmp/e0_$$.txt | tr -d ' ')
    [ -f data/e0_sets/${r}_$h.txt ] || cp /tmp/e0_$$.txt data/e0_sets/${r}_$h.txt
    echo "$ts,$i,rest,$r,$c,$h" >> "$OUT"
    # gcloud
    gcloud iam roles describe roles/$r --format=json 2>/dev/null \
      | jq -r '.includedPermissions[]?' | LC_ALL=C sort -u > /tmp/e0_$$.txt
    h=$(shasum -a 256 /tmp/e0_$$.txt | cut -c1-16); c=$(wc -l < /tmp/e0_$$.txt | tr -d ' ')
    [ -f data/e0_sets/${r}_$h.txt ] || cp /tmp/e0_$$.txt data/e0_sets/${r}_$h.txt
    echo "$ts,$i,gcloud,$r,$c,$h" >> "$OUT"
  done
  [ "$i" -lt "$N" ] && sleep "$GAP"
done
rm -f /tmp/e0_$$.txt
echo DONE >> "data/e0_${LABEL}.done"

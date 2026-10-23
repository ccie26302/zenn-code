#!/bin/bash
# E6: 稼働時間のチェック(証明書の検証あり)の合否を、直近の時間で数える
cd "$(dirname "$0")"; P=$(cat ../project.txt); T=$(gcloud auth print-access-token)
S=$(date -u -v-30M +%Y-%m-%dT%H:%M:%SZ); E=$(date -u +%Y-%m-%dT%H:%M:%SZ)
curl -s -G -H "Authorization: Bearer $T" "https://monitoring.googleapis.com/v3/projects/$P/timeSeries" \
  --data-urlencode 'filter=metric.type="monitoring.googleapis.com/uptime_check/check_passed"' \
  --data-urlencode "interval.startTime=$S" --data-urlencode "interval.endTime=$E" | python3 -c "
import sys,json,collections
d=json.load(sys.stdin); c=collections.defaultdict(lambda:[0,0]); reg=collections.defaultdict(set)
for ts in d.get('timeSeries',[]):
    cid=ts['metric']['labels'].get('check_id'); reg[cid].add(ts['metric']['labels'].get('checker_location'))
    for p in ts['points']:
        c[cid][0 if p['value'].get('boolValue') else 1]+=1
print('window', '$S', '$E')
for k,(ok,ng) in sorted(c.items()): print(k,'passed',ok,'failed',ng,'locations',len(reg[k]))
"

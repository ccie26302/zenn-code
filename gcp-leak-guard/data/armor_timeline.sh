#!/bin/bash
# 新しいロードバランサ＋Cloud Armor に、30秒ごとに40回送り、応答コードの内訳を記録する(応答し始める時刻と、429 が返り始める時刻を測る)
# 応答がない(000)うちは1回だけ試す。usage: PROJECT_ID=xxx ./data/armor_timeline.sh MINUTES
P=${PROJECT_ID:?}; N=${1:-15}
IP=$(gcloud --project $P compute forwarding-rules describe api-fr --global --format='value(IPAddress)')
end=$(( $(date +%s) + N*60 ))
while [ "$(date +%s)" -lt $end ]; do
  first=$(curl -s -m 3 -o /dev/null -w '%{http_code}' "http://$IP/items/00000000-0000-0000-0000-000000000000")
  if [ "$first" = 000 ]; then echo "$(date -u +%H:%M:%S)  no response (000)"
  else c=$(for j in $(seq 1 39); do curl -s -m 3 -o /dev/null -w '%{http_code}\n' "http://$IP/items/00000000-0000-0000-0000-000000000000"; done | sort | uniq -c | tr -s ' ' | tr '\n' ' ')
       echo "$(date -u +%H:%M:%S)  first=$first then:$c"; fi
  sleep 30
done

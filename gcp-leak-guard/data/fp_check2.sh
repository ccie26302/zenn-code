#!/bin/bash
# 直したフィルタで、E: なりすましの無効化は鳴り、F: 週次の再デプロイは鳴らないことを確かめる(SA のなりすまし権限が要る)
P=${PROJECT_ID:?}; R=asia-northeast1; OUT=data/fp_check.txt; SA=patch-runner@$P.iam.gserviceaccount.com
g() { gcloud --project "$P" --quiet "$@"; }
pull() { g pubsub subscriptions pull security-alerts-sub --auto-ack --limit 20 --format=json 2>/dev/null | python3 -c "
import json,sys,base64
for x in json.load(sys.stdin):
  m=x['message']; d=m['data']; inc=json.loads(base64.urlsafe_b64decode(d+'='*(-len(d)%4)))['incident']
  print(m['publishTime'], inc['policy_name'], inc['state'], inc.get('started_at'))"; }
g pubsub subscriptions seek security-alerts-sub --time="$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null
echo "## E: new filter. owner impersonates patch-runner and toggles, start $(date -u +%T)" >> $OUT
g run services update api --region $R --invoker-iam-check --impersonate-service-account=$SA >/dev/null 2>&1
g run services update api --region $R --no-invoker-iam-check --impersonate-service-account=$SA >/dev/null 2>&1
echo "toggled $(date -u +%T)" >> $OUT
for i in $(seq 1 30); do n=$(pull | tee -a $OUT | wc -l); [ "$n" -gt 0 ] && break; sleep 15; done
echo "## F: new filter. weekly job, start $(date -u +%T) (waiting >5 min after E so the rate limit does not hide it)" >> $OUT
sleep 330
g pubsub subscriptions seek security-alerts-sub --time="$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null
g scheduler jobs run weekly-patch --location $R; sleep 5
B=$(g builds list --region $R --limit 1 --format='value(id)')
until s=$(g builds describe $B --region $R --format='value(status)'); [ "$s" != WORKING ] && [ "$s" != QUEUED ]; do sleep 10; done
echo "build $s, finished $(g builds describe $B --region $R --format='value(finishTime)')" >> $OUT
for i in $(seq 1 24); do pull >> $OUT; sleep 15; done
echo "## end $(date -u +%T)" >> $OUT

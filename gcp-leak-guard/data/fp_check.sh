#!/bin/bash
# 週次の再デプロイ(patch-runner)では鳴らず、人の手による IAM チェックの無効化では鳴るかを確かめる
P=${PROJECT_ID:?}; R=asia-northeast1; OUT=data/fp_check.txt
g() { gcloud --project "$P" --quiet "$@"; }
pull() { g pubsub subscriptions pull security-alerts-sub --auto-ack --limit 20 --format=json 2>/dev/null | python3 -c "
import json,sys,base64
for x in json.load(sys.stdin):
  m=x['message']; d=m['data']; inc=json.loads(base64.urlsafe_b64decode(d+'='*(-len(d)%4)))['incident']
  print(m['publishTime'], inc['policy_name'], inc['state'], inc.get('started_at'))"; }
g pubsub subscriptions seek security-alerts-sub --time="$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null
echo "## A: weekly job (patch-runner redeploys api), start $(date -u +%T)" >> $OUT
g scheduler jobs run weekly-patch --location $R; sleep 5
B=$(g builds list --region $R --limit 1 --format='value(id)')
until s=$(g builds describe $B --region $R --format='value(status)'); [ "$s" != WORKING ] && [ "$s" != QUEUED ]; do sleep 10; done
echo "build $s, finished $(g builds describe $B --region $R --format='value(finishTime)')" >> $OUT
for i in $(seq 1 24); do pull >> $OUT; sleep 15; done   # 6分待つ
echo "## B: owner toggles --invoker-iam-check / --no-invoker-iam-check, start $(date -u +%T)" >> $OUT
g run services update api --region $R --invoker-iam-check >/dev/null 2>&1
g run services update api --region $R --no-invoker-iam-check >/dev/null 2>&1
echo "toggled $(date -u +%T)" >> $OUT
for i in $(seq 1 40); do n=$(pull | tee -a $OUT | wc -l); [ "$n" -gt 0 ] && break; sleep 15; done
echo "## end $(date -u +%T)" >> $OUT

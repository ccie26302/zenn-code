#!/bin/bash
# アラートが届くまでの時間を測る(検証用のプロジェクト専用。api を一瞬 allUsers に公開し、IAM チェックの設定を切り替える)。
# 開いたままのインシデントへの再通知を測らないよう、試行ごとに baseline.sh と同じ条件のポリシーを "tN: ..." の名前で作り直し、
# 新しいインシデントの最初の通知を測る。起点は監査ログの timestamp、終点は Pub/Sub の publishTime。
# 事前に: baseline.sh の detect(通知チャネル security-alerts と、そのトピック)、SA leak-test(権限なし)、api サービス
# 作ったばかりのログベースのアラートはすぐには効かない(作成3分後の操作では4つ中1つしか発火せず、16分後は全部発火した)。
# そのため、ポリシーを作る(create)のと、操作して測る(run)のを分け、間を15分以上空ける。
# 試行用のポリシーは1回分だけ作ること。次の回のポリシーを先に作っておくと、前の回の操作で発火してしまい、5分の通知間隔の制限で測れない(試行3はこれで無効にした)。
# usage: PROJECT_ID=xxx ./data/alert_trial.sh create TRIAL   → 15分以上待つ →   PROJECT_ID=xxx ./data/alert_trial.sh run TRIAL
set -uo pipefail
P=${PROJECT_ID:?}; R=${REGION:-asia-northeast1}; MODE=${1:?}; T=${2:?}; OUT=data/alerts.csv; RAW=data/raw_alerts; mkdir -p "$RAW"
umask 077
g() { gcloud --project "$P" --quiet "$@"; }
[ -f "$OUT" ] || echo "trial,event,audit_ts,incident_started,publish_ts,latency_s,state" > "$OUT"
SUB=security-alerts-trial   # 本番の購読の未読を捨てないよう、試験専用の購読で受ける
g pubsub subscriptions describe $SUB >/dev/null 2>&1 || g pubsub subscriptions create $SUB --topic security-alerts >/dev/null
CH=$(g beta monitoring channels list --filter='displayName="security-alerts"' --format='value(name)' | head -1)
TB=gs://$P-alert-test   # public access prevention を付けない空のバケット(公開の付与を検知できるかの確認用)
g storage buckets describe $TB >/dev/null 2>&1 || g storage buckets create $TB --location "$R" --uniform-bucket-level-access --no-public-access-prevention >/dev/null

A='logName:"cloudaudit.googleapis.com%2Factivity"'
PUB='(protoPayload.methodName:"SetIamPolicy" OR protoPayload.methodName="storage.setIamPermissions") AND ((protoPayload.serviceData.policyDelta.bindingDeltas.action="ADD" AND (protoPayload.serviceData.policyDelta.bindingDeltas.member:"allUsers" OR protoPayload.serviceData.policyDelta.bindingDeltas.member:"allAuthenticatedUsers")) OR protoPayload.request.policy.bindings.members:"allUsers" OR protoPayload.request.policy.bindings.members:"allAuthenticatedUsers")'
filt() { case $1 in   # macOS の bash 3.2 でも動くよう連想配列を使わない
  key_create) echo "$A AND protoPayload.methodName=\"google.iam.admin.v1.CreateServiceAccountKey\"";;
  public_run) echo "$A AND protoPayload.serviceName=\"run.googleapis.com\" AND $PUB";;
  public_gcs) echo "$A AND protoPayload.serviceName=\"storage.googleapis.com\" AND $PUB";;
  invoker_disabled) echo "$A AND protoPayload.serviceName=\"run.googleapis.com\" AND (protoPayload.request.service.invokerIamDisabled=true OR protoPayload.request.service.metadata.annotations.\"run.googleapis.com/invoker-iam-disabled\"=\"true\")";;
esac; }
if [ "$MODE" = create ]; then
  for e in key_create public_run public_gcs invoker_disabled; do
    python3 - "t$T: $e" "$(filt $e)" "$CH" > "$RAW/policy.json" <<'PY'
import json, sys
n, f, ch = sys.argv[1:4]
print(json.dumps({"displayName": n, "combiner": "OR", "conditions": [{"displayName": n, "conditionMatchedLog": {"filter": f}}],
  "alertStrategy": {"notificationRateLimit": {"period": "300s"}, "autoClose": "1800s"}, "notificationChannels": [ch]}))
PY
    g monitoring policies create --policy-from-file="$RAW/policy.json" >/dev/null
  done
  rm -f "$RAW/policy.json"
  echo "t$T: policies created at $(date -u +%H:%M:%S). 15分以上おいてから run を実行"; exit 0
fi
g pubsub subscriptions seek $SUB --time="$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null   # 古い通知を捨てる
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)

K=$(mktemp); trap 'rm -f "$K"' EXIT
g iam service-accounts keys create "$K" --iam-account="leak-test@$P.iam.gserviceaccount.com" >/dev/null 2>&1
KID=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['private_key_id'])" "$K"); rm -f "$K"
g iam service-accounts keys delete "$KID" --iam-account="leak-test@$P.iam.gserviceaccount.com" >/dev/null 2>&1
g run services add-iam-policy-binding api --region "$R" --member=allUsers --role=roles/run.invoker >/dev/null 2>&1
g run services remove-iam-policy-binding api --region "$R" --member=allUsers --role=roles/run.invoker >/dev/null 2>&1
g storage buckets add-iam-policy-binding $TB --member=allUsers --role=roles/storage.objectViewer >/dev/null 2>&1
g storage buckets remove-iam-policy-binding $TB --member=allUsers --role=roles/storage.objectViewer >/dev/null 2>&1
g run services update api --region "$R" --invoker-iam-check >/dev/null 2>&1
g run services update api --region "$R" --no-invoker-iam-check >/dev/null 2>&1
echo "t$T: operations done at $(date -u +%H:%M:%S)"

: > "$RAW/t${T}_msgs.jsonl"
for i in $(seq 1 60); do
  g pubsub subscriptions pull $SUB --auto-ack --limit 20 --format=json 2>/dev/null | python3 -c "
import json, sys
for x in json.load(sys.stdin): print(json.dumps(x['message']))" >> "$RAW/t${T}_msgs.jsonl"
  n=$(python3 - "$RAW/t${T}_msgs.jsonl" "t$T: " <<'PY'
import json, sys, base64
seen = set()
for line in open(sys.argv[1]):
    m = json.loads(line); d = m["data"]
    inc = json.loads(base64.urlsafe_b64decode(d + "=" * (-len(d) % 4)))["incident"]   # data は URL-safe Base64
    if inc["policy_name"].startswith(sys.argv[2]): seen.add(inc["policy_name"])
print(len(seen))
PY
)
  [ "$n" -ge 4 ] && break; sleep 10
done

# 監査ログの時刻(起点)を取り、通知と突き合わせる
g logging read "$A AND timestamp>=\"$START\" AND (protoPayload.methodName=\"google.iam.admin.v1.CreateServiceAccountKey\" OR protoPayload.methodName:\"SetIamPolicy\" OR protoPayload.methodName=\"storage.setIamPermissions\" OR protoPayload.methodName:\"ReplaceService\" OR protoPayload.methodName:\"UpdateService\")" \
  --format=json --freshness=1h > "$RAW/t${T}_audit.json"
python3 - "$T" "$RAW/t${T}_msgs.jsonl" "$RAW/t${T}_audit.json" >> "$OUT" <<'PY'
import json, sys, base64, datetime, re
T, msgs, audit = sys.argv[1], sys.argv[2], sys.argv[3]
def ts(s):
    s = s.replace("Z", "+00:00"); m = re.match(r"(.*\.\d{1,6})\d*(\+.*)", s)   # Python 3.9 はナノ秒を読めない
    return datetime.datetime.fromisoformat(m.group(1) + m.group(2) if m else s).timestamp()
first = {}
for e in json.load(open(audit)):
    p = e["protoPayload"]; m = p.get("methodName", ""); s = json.dumps(p)
    if "CreateServiceAccountKey" in m: k = "key_create"
    elif m == "storage.setIamPermissions" and '"ADD"' in s and "allUsers" in s: k = "public_gcs"
    elif "SetIamPolicy" in m and p.get("serviceName") == "run.googleapis.com" and "allUsers" in s: k = "public_run"   # 外す側の新しいポリシーには allUsers が無い
    elif p.get("serviceName") == "run.googleapis.com" and re.search(r'"invokerIamDisabled": true|invoker-iam-disabled": "true"', s, re.I): k = "invoker_disabled"   # 注釈の値は "True"
    else: continue
    first[k] = min(first.get(k, 1e12), ts(e["timestamp"]))
got = {}
for line in open(msgs):
    m = json.loads(line); d = m["data"]
    inc = json.loads(base64.urlsafe_b64decode(d + "=" * (-len(d) % 4)))["incident"]
    if not inc["policy_name"].startswith(f"t{T}: "): continue
    k = inc["policy_name"].split(": ", 1)[1]
    if k not in got: got[k] = (ts(m["publishTime"]), inc.get("started_at"), inc.get("state"))
for k in ["key_create", "public_run", "public_gcs", "invoker_disabled"]:
    a = first.get(k); pub, started, state = got.get(k, (None, None, None))
    lat = f"{pub - a:.1f}" if a and pub else ""
    print(f"{T},{k},{a or ''},{started or ''},{pub or ''},{lat},{state or 'NOT_RECEIVED'}")
PY
for n in $(g monitoring policies list --filter="displayName:\"t$T: \"" --format='value(name)'); do g monitoring policies delete "$n" >/dev/null; done
grep "^$T," "$OUT"

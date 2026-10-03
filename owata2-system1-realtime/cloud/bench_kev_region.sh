#!/bin/zsh
# Vertex AI のカスタム推論(L4)に置いた kev-4b を測って撤去する。usage: PROJECT_ID=<id> cloud/bench_kev_region.sh <tag> <region>
# 失敗しても必ず撤去する。UNLINK_BILLING=1 のときだけ、最後に課金を外す(検証専用プロジェクト向け)。
cd "$(dirname "$0")/.."
LOG=logs/bench_${1}.log; exec >> $LOG 2>&1
TAG=$1; P=${PROJECT_ID:?PROJECT_ID を指定}; R=$2; N=$(gcloud projects describe $P --format="value(projectNumber)"); DLOG=logs/deploy_${TAG}.log
say() { echo "$(date '+%H:%M:%S') $*"; }
cleanup() {
  say "撤去開始"; pkill -f gpu_proxy.py
  TOKEN=$(gcloud auth print-access-token)
  for i in 1 2 3 4 5 6 7 8; do
    J=$(curl -s -H "Authorization: Bearer $TOKEN" "https://$R-aiplatform.googleapis.com/v1/projects/$N/locations/$R/endpoints")
    EPS=$(echo "$J" | python3 -c "import json,sys;d=json.load(sys.stdin);[print(e['name'].split('/')[-1], ' '.join(m['id'] for m in e.get('deployedModels',[]))) for e in d.get('endpoints',[])]")
    [ -z "$EPS" ] && break
    echo "$EPS" | while read ep dms; do
      for dm in ${=dms}; do curl -s -X POST -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' -d "{\"deployedModelId\":\"$dm\"}" "https://$R-aiplatform.googleapis.com/v1/projects/$N/locations/$R/endpoints/$ep:undeployModel" >/dev/null; done
      [ -z "$dms" ] && curl -s -X DELETE -H "Authorization: Bearer $TOKEN" "https://$R-aiplatform.googleapis.com/v1/projects/$N/locations/$R/endpoints/$ep" >/dev/null
    done
    sleep 60
  done
  for m in $(gcloud ai models list --region $R --project $P --format="value(name.basename())" 2>/dev/null); do curl -s -X DELETE -H "Authorization: Bearer $TOKEN" "https://$R-aiplatform.googleapis.com/v1/projects/$N/locations/$R/models/$m" >/dev/null; done
  sleep 30
  say "撤去後 endpoints=$(gcloud ai endpoints list --region $R --project $P --format='value(name)' 2>/dev/null | wc -l | tr -d ' ') models=$(gcloud ai models list --region $R --project $P --format='value(name)' 2>/dev/null | wc -l | tr -d ' ')"
  # Gemini の計測が終わってから課金を外す
  while pgrep -f "bench/latency.py gemini" >/dev/null; do sleep 30; done
  if [ "${UNLINK_BILLING:-0}" = 1 ]; then gcloud billing projects unlink $P >/dev/null 2>&1; fi; say "billing=$(gcloud billing projects describe $P --format='value(billingEnabled)')"
}
trap cleanup EXIT
while pgrep -f "gpu_endpoint.py deploy $TAG" >/dev/null; do sleep 30; done
if ! grep -q '"status": "ready"' $DLOG; then say "デプロイ失敗"; tail -3 $DLOG; exit 1; fi
say "READY $(grep deploy_min $DLOG)"
EP=$(python3 -c "import json;print(json.load(open('data/endpoints.json'))['$TAG']['endpoint'].split('/')[-1])")
say "起動ログ: $(gcloud logging read "resource.labels.endpoint_id=\"$EP\" AND (jsonPayload.message:\"serving jaredpalmer\" OR textPayload:\"serving jaredpalmer\")" --project $P --freshness=90m --limit 1 --format="value(jsonPayload.message,textPayload)" 2>/dev/null | head -1)"
nohup uv run --with httpx --with google-auth --with requests --with fastapi --with uvicorn cloud/gpu_proxy.py $TAG 8091 > logs/gpu_proxy.log 2>&1 &
for i in $(seq 1 60); do curl -s -m 2 localhost:8091/health | grep -q ok && break; sleep 2; done
# 専用エンドポイントが 404 を返す数分間を待つ
for i in $(seq 1 30); do python3 bench/latency.py probe http://127.0.0.1:8091/v1/systemone 1 0 >/dev/null 2>&1 && break; sleep 20; done
rm -f data/bench/probe_*
python3 bench/latency.py kev-4b_vertex_${TAG} http://127.0.0.1:8091/v1/systemone 300 20
DNS=$(python3 -c "import json;print(json.load(open('data/endpoints.json'))['$TAG']['dns'])")
bench/net.sh $DNS 50
# 放置後の初回: 60秒あけて1回ずつ、10回
TAG=$TAG python3 - <<'PY'
import json, time, urllib.request, csv, os
body = json.dumps({"state": "横スクロールのアクションゲーム。目的: 画面の右端まで進んで、次のステージへ行くこと。\n自機: x=99, y=302。", "model": "latest",
    "questions": {"move": {"type": "choice", "instructions": "次の操作(約0.1秒)を1つ選ぶ。", "criteria": {"A": "右へ歩く", "B": "右へジャンプ", "C": "何もしない"}}}}).encode()
rows = []
for i in range(10):
    time.sleep(60); t = time.perf_counter()
    r = json.loads(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8091/v1/systemone", body, {"content-type": "application/json"}), timeout=120).read())
    rows.append({"i": i, "client_ms": round((time.perf_counter() - t) * 1000, 1), "gpu_ms": r.get("gpu_ms"), "remote_ms": round(r.get("remote_ms", 0), 1)})
    print(rows[-1], flush=True)
w = csv.DictWriter(open(f"data/bench/kev-4b_vertex_{os.environ['TAG']}_idle60s_{time.strftime('%Y%m%d-%H%M%S')}.csv", "w", newline=""), fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
PY
say "計測完了"

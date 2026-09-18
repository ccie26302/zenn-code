# 再現手順: Gemini の間接プロンプトインジェクション耐性(1,509試行)

このディレクトリのスクリプトとコーパスで、記事の全測定を再現できます。
`PROJECT_ID` を自分の値に置き換えてください。

## 前提

- gcloud SDK 582 以降。`--functional-type` / `--identity-type` は **alpha にしかありません**
- 組織なしの個人プロジェクトで動きます
- Vertex のロケーションは `global`(5モデル全部が通る唯一のロケーション)
- 課金は Cloud Run、Artifact Registry、Cloud Build、Gemini 呼び出し分。
  Model Armor は月200万トークン無料の範囲

## ファイル

| ファイル | 役割 |
|---|---|
| `app/main.py` | front / back / sink を `ROLE` で切り替える1つのコンテナ |
| `corpus.json` | 凍結した攻撃12本・良性12本 |
| `corpus_tool.json` | ツール出力に仕込む注入3本(T01–T03)+対照(T00) |
| `corpus_same.json` | T01–T03 と一字一句同じ文字列を文書に埋めたもの(D01–D03) |
| `corpus_mech.json` | 動作数だけを分離する6本(M1A–M3B)。事前登録済み |
| `run_z0.py` | 前作の「拒否」を確かめ直す |
| `run_ceiling.py` | 能力天井 |
| `run_sweep.py` | モデル別の本測定 |
| `run_sweepA.py` | 利用者の依頼を揃えた文書経由 |
| `run_sweepC.py` | さらに back を良性の固定文字列にした対照 |
| `run_toolinj.py` | ツール出力経由の注入 |
| `run_same.py` | 同一文字列を文書に埋めた対照 |
| `run_mech.py` | 動作数だけを分離する実験 |
| `run_x4b.py` | メタデータ識別(5群) |
| `analyze_sweep.py` / `analyze_logs.py` | 集計 |

`app/main.py` は前作から3点変わっています。再現にはこの差分が必要です。

1. `payload["model"]` / `["location"]` でリクエストごとにモデルを切り替える
2. `payload["inject_response"]` を渡すと back がシークレットも Gemini も呼ばずに
   その文字列をそのまま返す(ツール出力経由の注入を再現するため)
3. `payload["fence"]` を渡すと、back の応答を文書と同じ形で囲んでから会話に連結する

## 手順

```bash
export PROJECT_ID=あなたのプロジェクトID
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export REGION=us-central1
export POOL="agents.global.proj-${PROJECT_NUMBER}.system.id.goog"
PRIN() { echo "principal://$POOL/resources/run/projects/$PROJECT_NUMBER/locations/$REGION/services/$1"; }

gcloud services enable run.googleapis.com aiplatform.googleapis.com secretmanager.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com logging.googleapis.com \
  modelarmor.googleapis.com --project=$PROJECT_ID

gcloud artifacts repositories create chain --repository-format=docker \
  --location=$REGION --project=$PROJECT_ID
( cd app && gcloud builds submit --tag=$REGION-docker.pkg.dev/$PROJECT_ID/chain/agent:v1 --project=$PROJECT_ID )
export IMG=$(gcloud artifacts docker images describe \
  $REGION-docker.pkg.dev/$PROJECT_ID/chain/agent:v1 \
  --format='value(image_summary.fully_qualified_digest)')

python3 -c "import secrets;print('canary-b-'+secrets.token_hex(10),end='')" \
  | gcloud secrets create chain-secret --data-file=- --project=$PROJECT_ID

# 順序が大事。agent-identity に切り替えるとプリンシパルが変わる
for r in sink back; do
  gcloud alpha run deploy agent-$r --image=$IMG --region=$REGION --project=$PROJECT_ID \
    --functional-type=agent --identity-type=agent-identity --no-allow-unauthenticated \
    --min-instances=1 \
    --set-env-vars=ROLE=$r,PROJECT_ID=$PROJECT_ID,REGION=$REGION,SECRET_NAME=chain-secret
done
gcloud secrets add-iam-policy-binding chain-secret \
  --member="$(PRIN agent-back)" --role=roles/secretmanager.secretAccessor --project=$PROJECT_ID

export BACK=$(gcloud run services describe agent-back --region=$REGION --project=$PROJECT_ID --format='value(status.url)')
export SINK=$(gcloud run services describe agent-sink --region=$REGION --project=$PROJECT_ID --format='value(status.url)')

gcloud alpha run deploy agent-front --image=$IMG --region=$REGION --project=$PROJECT_ID \
  --functional-type=agent --identity-type=agent-identity --no-allow-unauthenticated \
  --min-instances=1 --timeout=600 \
  --set-env-vars=ROLE=front,PROJECT_ID=$PROJECT_ID,REGION=$REGION,BACK_URL=$BACK,SINK_URL=$SINK,MAX_TURNS=3

for svc in agent-back agent-sink; do
  gcloud run services add-iam-policy-binding $svc --region=$REGION --project=$PROJECT_ID \
    --member="$(PRIN agent-front)" --role=roles/run.invoker --quiet
done

# 呼び出す本人にも invoker が要る。忘れると全部 403
gcloud run services add-iam-policy-binding agent-front --region=$REGION --project=$PROJECT_ID \
  --member="user:$(gcloud config get-value account)" --role=roles/run.invoker

for a in agent-front agent-back; do
  gcloud projects add-iam-policy-binding $PROJECT_ID --member="$(PRIN $a)" --role=roles/aiplatform.user --quiet
done

gcloud run services describe agent-front --region=$REGION --project=$PROJECT_ID \
  --format='value(status.url)' > FRONT_URL.txt
python3 -c "import json;json.dump({m:'global' for m in ['gemini-2.5-flash','gemini-2.5-pro','gemini-3.5-flash','gemini-3.8-flash','gemini-3-flash-preview']},open('models_ok.json','w'))"
```

測定は上から順に流せます。

```bash
python3 run_z0.py 2 gemini-2.5-flash   #  48試行
python3 run_ceiling.py 5               #  25試行
python3 run_sweep.py 5 3               # 480試行
python3 run_toolinj.py                 # 100試行
python3 run_sweepA.py 3 0              # 180試行
python3 run_sweepC.py 3 0              # 180試行(back を固定)
python3 run_same.py                    #  75試行
python3 run_mech.py                    # 150試行(動作数の分離)
python3 run_x4b.py                     #  60試行
python3 analyze_sweep.py               # 集計
```

## Model Armor

```bash
gcloud model-armor templates create x5-log --location=$REGION --project=$PROJECT_ID \
  --pi-and-jailbreak-filter-settings-enforcement=enabled \
  --pi-and-jailbreak-filter-settings-confidence-level=low-and-above \
  --template-metadata-log-sanitize-operations

export TOK=$(gcloud auth print-access-token)
curl -s -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"userPromptData":{"text":"判定したい文字列"}}' \
  "https://modelarmor.${REGION}.rep.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/templates/x5-log:sanitizeUserPrompt"

# フィルタ版の移行予告はここにしか出ない
gcloud logging read 'LOG_ID("modelarmor.googleapis.com/sanitize_operations")' \
  --project=$PROJECT_ID --limit=1 --format=json --freshness=1h \
  | python3 -c "import json,sys;print(json.dumps(json.load(sys.stdin)[0]['jsonPayload']['sanitizationResult']['sanitizationMetadata'],ensure_ascii=False,indent=1))"
```

## 監査ログ

既定では無効なので有効化が要ります。

```bash
gcloud projects get-iam-policy $PROJECT_ID --format=json > /tmp/pol.json
python3 - <<'PY'
import json
p=json.load(open('/tmp/pol.json'))
ac=p.get('auditConfigs',[])
have={c['service'] for c in ac}
for svc in ('aiplatform.googleapis.com','modelarmor.googleapis.com'):
    if svc not in have:
        ac.append({"service":svc,"auditLogConfigs":[{"logType":"DATA_READ"}]})
p['auditConfigs']=ac
json.dump(p,open('/tmp/pol.json','w'))
PY
gcloud projects set-iam-policy $PROJECT_ID /tmp/pol.json
```

`--freshness` は広めに(30d 程度)取ってください。既定だと少し前の試行が拾えず、
「ログが出ていない」と誤認します。

## 後片付け

```bash
for s in agent-front agent-back agent-sink; do
  gcloud run services delete $s --region=$REGION --project=$PROJECT_ID --quiet
done
gcloud secrets delete chain-secret --project=$PROJECT_ID --quiet
gcloud artifacts repositories delete chain --location=$REGION --project=$PROJECT_ID --quiet
for t in x5-log x5-latest; do
  gcloud model-armor templates delete $t --location=$REGION --project=$PROJECT_ID --quiet 2>/dev/null
done
gcloud projects remove-iam-policy-binding $PROJECT_ID \
  --member="principalSet://${POOL}/attribute.platformContainer/run/projects/${PROJECT_NUMBER}" \
  --role=roles/run.agentDefaultAccess
```

中断するときは `--min-instances=0` に落とすとアイドル課金が止まります。

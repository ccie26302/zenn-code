# 再現手順

Gemini 4 Argon を Google Cloud の従量課金で呼び、Gemini CLI をエージェントとして隔離したコンテナで動かした検証の手順です。記事: https://zenn.dev/ccie26302/articles/zenn-argon-vertex-paygo

費用の目安(導入価格): A の API 測定で約1ドル、B(17課題×3回)で約4ドル、C(承認モード・ポリシー・.env、20課題で計約100試行)で約3ドル。

## 0. 前提

- macOS(Apple Silicon)、colima、Docker CLI、Python 3.13、gcloud
- 課金を有効にした検証用のプロジェクト

```bash
export PROJECT_ID=your-project-id
python3.13 -m venv .venv && .venv/bin/pip install google-genai==2.30.1
colima start --cpu 4 --memory 8 --vm-type vz
```

## 1. 推論の権限だけのサービスアカウント

```bash
gcloud services enable aiplatform.googleapis.com --project $PROJECT_ID
gcloud iam roles create argonPredictOnly --project $PROJECT_ID --title "Argon predict only" \
  --permissions aiplatform.endpoints.predict --stage GA
gcloud iam service-accounts create argon-agent --project $PROJECT_ID
SA=argon-agent@$PROJECT_ID.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding $PROJECT_ID --condition=None \
  --member serviceAccount:$SA --role projects/$PROJECT_ID/roles/argonPredictOnly
gcloud iam service-accounts add-iam-policy-binding $SA --project $PROJECT_ID \
  --member user:$(gcloud config get-value account) --role roles/iam.serviceAccountTokenCreator
```

## 2. A: API の測定

```bash
cd api
../.venv/bin/python a_api.py A1loc a1.csv     # 呼べる location
../.venv/bin/python a_api.py A1lat a1.csv     # 東京からの遅延
../.venv/bin/python a_api.py A1tier a1.csv    # Priority / Flex
../.venv/bin/python a_api.py A5 a5.csv        # パラメータの制約
../.venv/bin/python a_api.py A5temp a5.csv    # temperature
../.venv/bin/python a4.py                     # countTokens と prompt_token_count(繰り返し)
JA_ARTICLES="<日本語の Markdown>/*.md" ../.venv/bin/python a4b.py   # 自然な文章
../.venv/bin/python a4c.py && ../.venv/bin/python a4d.py && ../.venv/bin/python a4e.py a4e.csv
../.venv/bin/python a4h.py                    # 上乗せの最小対と candidate_count
```

A2(エラーの段階)は、権限なしの SA と、課金を付けない使い捨てのプロジェクトを作ってから `a2.py` を流します(プロジェクト名は `api/a2_project.txt` に書く)。

## 3. B・C: エージェント

```bash
cd harness
docker build -t argon-proxy proxy && docker build -t argon-agent agent
ALLOW_MODELS=gemini-4-argon ./up.sh          # 中継と --internal ネットワーク
nohup ./refresh_token.sh &                     # なりすましのトークンを30分ごとに更新
cd ../tasks && ./validate.sh                   # 全課題の3点検証(初期状態は不合格、模範解答は合格、惜しい誤答は不合格)
cd ../harness && ./main.sh                     # B: 17課題×3回(CLI の既定)
./c.sh                                         # C: 承認モード・ポリシー・.env の9課題×3回
SETTINGS=HIGH ./trial.py HIGH B1_05 1          # 3/3 にならなかった課題を HIGH で(r1〜r3)
./add.sh                                       # レビュー後の追加(書き方を変えた依頼、.env、plan の反復、設定なしの CLI)
cd .. && .venv/bin/python report.py > REPORT.md
```

1試行は `harness/trial.py COND TASK REP` です。結果は `runs/<COND>/<TASK>/r<REP>/` に、エージェントの出力(stream-json)、中継が記録した要求、判定、1行の集計(row.json)として残ります。

## 4. 片付け

```bash
docker rm -f argon-proxy && docker network rm argon-int
gcloud iam service-accounts delete argon-agent@$PROJECT_ID.iam.gserviceaccount.com --project $PROJECT_ID
gcloud iam roles delete argonPredictOnly --project $PROJECT_ID
```

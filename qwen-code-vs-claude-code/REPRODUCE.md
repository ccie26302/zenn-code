# 再現手順

Qwen Code(2つの構成)と Claude Code に、同じ43の課題を同じ隔離の中で3回ずつ解かせ、合格・時間・費用を測る手順です。上から順にコピーして流せます。`<...>` は自分の値に置き換えてください。

## 0. 前提

- macOS(Apple Silicon、メモリ 64GB 以上。手元の 27B を動かすため)
- colima と docker、Ollama 0.32 系、gcloud CLI、Python 3.12 以上
- Google Cloud のプロジェクトを2つ
  - 管理用(`<model-project>`): Agent Platform のモデル(Qwen3-Coder 480B の MaaS)を有効にし、サービスアカウント3つを置く
  - 使い捨ての対象(`<target-project>`): 組織に属さない新しいプロジェクト。エージェントはここだけを触る。予算のアラートを付ける
- Claude Code を流すなら Claude のサブスク(長期トークンを発行する)

```bash
export M=<model-project> P=<target-project>
cd harness && echo $P > target_project.txt
```

## 1. イメージとモデル

```bash
docker build -t qwen-agent agent     # Qwen Code 0.25.2、Claude Code 2.1.302、ffmpeg ほか、gcloud、Terraform とプロバイダのミラー
docker build -t qwen-proxy proxy     # モデルの中継と、Google Cloud への出口(mitmproxy)
ollama pull qwen3.8:27b && ollama create qwen3.8-27b-ctx64k -f ollama/Modelfile
```

## 2. サービスアカウントとロール

```bash
for sa in qwen-agent qwen-judge qwen-model; do gcloud iam service-accounts create $sa --project $M; done
gcloud iam roles create qwenPredictOnly --project $M --file iam/qwenPredictOnly.yaml
gcloud projects add-iam-policy-binding $M --member serviceAccount:qwen-model@$M.iam.gserviceaccount.com --role projects/$M/roles/qwenPredictOnly
gcloud iam roles create qwenAgent --project $P --file iam/qwenAgent.yaml
gcloud iam roles create qwenJudge --project $P --file iam/qwenJudge.yaml
gcloud projects add-iam-policy-binding $P --member serviceAccount:qwen-agent@$M.iam.gserviceaccount.com --role projects/$P/roles/qwenAgent
gcloud projects add-iam-policy-binding $P --member serviceAccount:qwen-judge@$M.iam.gserviceaccount.com --role projects/$P/roles/qwenJudge
```

Cloud Run の実行用に権限ゼロの SA を作り、エージェントにはその SA の単位でだけ serviceAccountUser を付けます。既定の Compute の SA に自動で付く Editor は外します。

```bash
gcloud iam service-accounts create qwen-run-rt --project $P
gcloud iam service-accounts add-iam-policy-binding qwen-run-rt@$P.iam.gserviceaccount.com --project $P \
  --member serviceAccount:qwen-agent@$M.iam.gserviceaccount.com --role roles/iam.serviceAccountUser
PN=$(gcloud projects describe $P --format='value(projectNumber)')
gcloud projects remove-iam-policy-binding $P --member serviceAccount:$PN-compute@developer.gserviceaccount.com --role roles/editor
```

自分のアカウントから3つの SA のトークンを発行できるようにします(なりすまし)。

```bash
for sa in qwen-agent qwen-judge qwen-model; do
  gcloud iam service-accounts add-iam-policy-binding $sa@$M.iam.gserviceaccount.com --project $M \
    --member user:$(gcloud config get account) --role roles/iam.serviceAccountTokenCreator
done
```

## 3. 秘密と中継

トークンは、コンテナには渡しません。中継が要求ごとに差し替えます。

```bash
mkdir -p secrets/model secrets/agent secrets/judge secrets/claude ctl ca cred logs && chmod 700 secrets/*
nohup ./refresh_tokens.sh > logs/refresh.log 2>&1 &      # 25分ごとに3つのトークンを更新する
./save_claude_token.sh                                   # C を流すときだけ。claude setup-token のトークンを secrets/claude/token に保存する
```

コンテナの gcloud は、どこにも登録していない使い捨ての鍵で「ログイン済み」にします(トークンの発行は中継がダミーで答えます)。

```bash
python3 - <<'PY'
import json, secrets, subprocess
pem = subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048"], capture_output=True, text=True, check=True).stdout
json.dump({"type": "service_account", "project_id": "x", "private_key_id": secrets.token_hex(20), "private_key": pem,
           "client_email": "qwen-agent@x.iam.gserviceaccount.com", "client_id": "1", "token_uri": "https://oauth2.googleapis.com/token"},
          open("cred/fake_sa.json", "w"))
PY
echo -n dummy > ctl/dummy_token && echo none > ctl/egress_mode
ALLOW_MODELS=qwen/qwen3-coder-480b-a35b-instruct-maas,qwen3.8-27b-ctx64k ./up.sh
```

## 4. 基準の状態と、負の対照

```bash
./gcp_state.sh snapshot base         # 試行の前に毎回この状態と比べ、判定のあとにここへ戻す
./negcontrol_run.sh negcontrol_result.csv    # やってよい操作が通り、やってはいけない操作が止まるか(30項目)
```

## 5. 判定の確認

各課題で、初期状態は不合格、模範解答は合格、惜しい誤答は不合格、別解は合格になるかを確かめます。

```bash
cd ../tasks
./validate.sh                                                     # 端末の課題(26本)
./gvalidate.sh $(ls -d G[0-9]*_[0-9]* T[0-9]*_[0-9]* | sort)     # Google Cloud の課題(17本。模範解答もエージェントと同じ権限・同じ中継で流す)
cd ../harness
```

## 6. 測定

```bash
caffeinate -i ./pilot.sh && caffeinate -i ./pilot_c.sh            # 予備試行(各課題を各構成で1回)
caffeinate -i ./main.sh                                           # 本測定(3構成 × 43課題 × 3回、混ぜて1本ずつ)
touch logs/STOP                                                   # 途中で止めるとき(今の試行の切れ目で止まる)
```

1回だけ流すとき:

```bash
./trial.py Q M1_01 1     # 構成(C・Q・L)、課題、回
```

## 7. 集計

```bash
cd .. && python3 report.py          # reports/main/ に summary.md、per_task.csv、rows.csv
python3 report.py PILOT_            # 予備試行
```

## 8. 片付け

```bash
gcloud projects delete $P
for sa in qwen-agent qwen-judge qwen-model; do gcloud iam service-accounts delete $sa@$M.iam.gserviceaccount.com --project $M -q; done
gcloud iam roles delete qwenPredictOnly --project $M
docker rm -f qwen-proxy && docker network rm qwen-int
```

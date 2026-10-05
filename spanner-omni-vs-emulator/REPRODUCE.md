# REPRODUCE

検証は M4 Max / macOS 26、Python 3.11、google-cloud-spanner 3.71.0、uv。性能は測らないでください(Spanner Omni ライセンス 3.4)。

## 0. 実行環境(colima)

```bash
brew install colima docker
colima start --cpu 4 --memory 8 --disk 40 --vm-type vz   # Developer edition は single-server・4 vCPU 以下なら期限なし
```

## 1. 3つのターゲット

```bash
# Spanner Omni(single-server)
docker volume create spanner
docker run -d --network host --name spanneromni -v "spanner:/spanner" \
  us-docker.pkg.dev/spanner-omni/images/spanner-omni:2026.r4-lts start-single-server
# エミュレータ
docker run -d --name spanneremu -p 9010:9010 -p 9020:9020 gcr.io/cloud-spanner-emulator/emulator:latest
# Cloud Spanner(90日の無料試用インスタンス)
export CLOUD_PROJECT=<検証用プロジェクト>
gcloud services enable spanner.googleapis.com --project $CLOUD_PROJECT
gcloud spanner instances create omni-truth --project $CLOUD_PROJECT --config=regional-asia-northeast1 \
  --instance-type=free-instance --description="omni truth free"
```

ADC(`gcloud auth application-default login`)の quota project が別のプロジェクトになっている場合でも、harness/targets.py は CLOUD_PROJECT を quota project として明示します。Cloud Monitoring へのクライアント指標の送信を止めるなら `export SPANNER_DISABLE_BUILTIN_METRICS=true`。

## 2. 本番(5ラウンド×3ターゲット)

```bash
export SPANNER_DISABLE_BUILTIN_METRICS=true
RUN_ID=main1 uv run python harness/orchestrate.py 5
# A9 は base64 の扱いを直したあと、3ターゲットで流し直した(監査で判明)。digest を残すなら OMNI_DIGEST・EMU_DIGEST を export してから流す
for r in 0 1 2 3 4; do for t in emu omni cloud; do RUN_ID=fix_a9 uv run --with 'google-cloud-spanner==3.71.0' python harness/run_v2.py $t $r A9; done; done
# A13 再起動(エミュレータと Omni のみ)
for t in emu omni; do for m in graceful kill9; do for r in 0 1 2 3 4; do
  uv run --with 'google-cloud-spanner==3.71.0' python harness/restart_test.py $t $m $r; done; done; done
```

## 3. 集計

```bash
python3 analyze.py main1 > data/v2/ANALYSIS.md        # 事前登録 v2.1 の規則どおり
python3 analyze_final.py > data/v2/FINDINGS.md        # 独立監査の反映後(結果を見たあとの変更点は先頭の docstring)
```

## 4. 事後の検証(事前登録の外)

```bash
for t in emu omni cloud; do uv run --with 'google-cloud-spanner==3.71.0' python posthoc/cell_boundary.py $t; done
for t in omni cloud; do uv run --with 'google-cloud-spanner==3.71.0' python posthoc/cell_bisect.py $t; done      # 1セルの最大
for t in omni cloud; do uv run --with 'google-cloud-spanner==3.71.0' python posthoc/mutation_bisect.py $t; done  # ミューテーション上限
for t in omni cloud; do uv run --with 'google-cloud-spanner==3.71.0' python posthoc/a3_control.py $t 20; done    # DDL なしの対照
```

## 5. 一次情報の取り込み(テストの母集団)

```bash
mkdir -p sources && cd sources
curl -sL 'https://docs.cloud.google.com/spanner/docs/emulator?hl=en' -o spanner_docs_emulator.html
curl -sL 'https://docs.cloud.google.com/spanner-omni/differences?hl=en' -o spanner-omni_differences.html
curl -sL https://raw.githubusercontent.com/GoogleCloudPlatform/cloud-spanner-emulator/master/README.md -o emulator_README.md
curl -sL https://raw.githubusercontent.com/google/zetasql/master/docs/functions-and-operators.md -o zetasql_functions.md
curl -sL 'https://docs.cloud.google.com/spanner/docs/reference/standard-sql/functions-all?hl=en' -o spanner_functions_all.html
```

関数の差集合は ZetaSQL の見出し(`## \`NAME\``)のうち、Spanner の関数一覧ページに大文字の語として現れないもの。抽出は `random.Random(20261005).sample(差集合, 20)`。

## 後片付け

```bash
gcloud spanner instances delete omni-truth --project $CLOUD_PROJECT
colima stop
```

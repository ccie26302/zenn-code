# REPRODUCE — Jev 互換の System-1 モデルに『人生オワタの大冒険2』を画面だけで遊ばせる

記事「画面だけのJev互換AIに人生オワタ2は早かった」の再現手順です。記事の数字はすべて、このフォルダで次を実行すると生データから出し直せます。

```bash
python3 report.py > data/REPORT.md
```

## 0. 前提

- Mac(Apple Silicon。検証は M4 Max / 128GB / macOS 26)、zsh、Node.js 24、Python 3.13、[uv](https://docs.astral.sh/uv/)、ffmpeg
- ゲームは作者キング氏の公式ページ(Ruffle で再公開、`harness/owata.mjs` の `URL_GAME`)をそのまま開きます。SWF やゲーム画面はこのリポジトリに含めていません
  - 『2』のページの FAQ に「配信や実況してもいいですか？ → いいよ！」とあります
  - ハーネスは広告・計測のリクエストを遮断し、ページの読み込みを最小限にします。作者の広告に無効な表示を積まないためです。ここは変えないでください
- Jev 本体(TypeSafe AI)は使っていません。比べたのは Jev と同じ `/v1/systemone` 形式で呼べる公開モデル kev-4b と laya-multilingual(laya-ml)です

```bash
cd harness && npm install && npx playwright install chromium && cd ..
```

## 1. 目のお手本を自分の画面から作る

お手本(自機の形・トゲの形・足場の形)はゲームの絵から切り出すので、リポジトリには入れていません。次の手順で作ります。

```bash
# 1面をランダムに動かして画面を集める(data/m1/frames/、frames.json、背景 data/m1/bg.png)
node harness/m1_collect.mjs
# 正解ラベル data/m1/labels_v3.json を付ける(形式は同梱のファイルを参照。乱数種と時計を固定しているので、同梱のラベルがそのまま合うことが多いが、必ず目視で確かめる)
# 背景との差分で自機の位置を出す → 自機のお手本(perception/player_templates.npz)
node harness/m1_predict.mjs
uv run --with numpy --with pillow python perception/templates.py
# トゲのお手本(perception/spike_template.npy)。足場のお手本は目のサーバが bg.png から起動時に切り出す
uv run --with numpy --with pillow python perception/make_spike_template.py
```

## 2. サーバを立てる

```bash
# 目(ルールの画像処理、AI なし) :8099
uv run --with numpy --with scipy --with pillow --with fastapi --with uvicorn perception/server.py 8099
# laya-ml(公式 PyTorch・多言語版・MPS) :8078   ※CPU で測るなら最後を cpu に
uv run --with 'laya==0.3.23' --with fastapi --with uvicorn servers/laya_py_server.py 8078 multilingual mps
# kev-4b(MLX) :8009   https://github.com/jaredpalmer/kev の手順で導入(検証はコミット 0fe8fc9)
python3 -m kev.serve --run jaredpalmer/kev-4b --port 8009
```

## 3. 試走

リアルタイム相当: ゲームの時計を Playwright の fake clock で止めて1コマずつ進め、判断にかかった実時間(目＋モデル)ぶんのコマを、手を離した状態で進めてから行動します。

```bash
# 最終比較(事前登録)を順番に回す: kev-4b 英語×3、laya-ml 英語×3、モデルだけ×2(10時間前後)
zsh harness/chain_final.sh
```

1本だけ回す場合(zsh。bash なら `env $C ...`):

```bash
cd harness
C="POLICY=systemone ACTSET=v3 MEMORY=gain ALPHA=0.5 GAMMA=1.0 STATKEY=coarse GAIN=net NOBAN=1 SOFTPEN=50 STATE_V=4 GOAL_X=640 REC=1 REC_ALL=1 EP=100 STEPS=80 LANG_=en"
env ${=C} MODEL_URL=http://127.0.0.1:8009/v1/systemone TAG=fin_kev_en_1 node run_play.mjs
```

主な環境変数(`harness/run_play.mjs`):

| 変数 | 意味 |
|---|---|
| ACTSET | v2 = 11択(大ジャンプは「右へ大ジャンプ(高い)」) / v3 = 同じ11択で大ジャンプを「ジャンプ」と呼び、小ジャンプより前に置く |
| STATE_V | 1 = 目的「右へ進むこと、死なないこと」 / 2 = 1＋トゲの列 / 3 = 目的「画面の右端まで進んで次のステージへ」＋向こう岸 / 4 = 3 の誤り(足場が止まっているときの文)を直し、英語でも目的と向こう岸 |
| LANG_ | ja / en |
| MEMORY | ban = 死んだ手を禁止(NOBAN=1 なら禁止もしない = モデルだけ) / gain = 前へ進めた行動を優先(足場に立てたら+100)＋未試行ボーナス |
| SOFTPEN | 死ぬ直前3手の経験点を 50, 25, 12.5 下げる(禁止はしない) |
| REC / REC_ALL | 試走中に全コマ録画(data/play/<TAG>/rec/。録画すると目が約15ms 遅くなる) |

ログは `data/play/<TAG>/episodes.jsonl`(1エピソード1行、各手の位置・行動・確率・遅れ・状態の文章)。このリポジトリには集計に使った21本分を入れています(録画は入れていません)。

足場に乗った回と死亡を録画で数え直す(CPU を多く使うので試走が終わってから)。目は S のポーズ中の自機を見失って死亡と誤判定することがあるので、死亡は death_check.py で確かめる:

```bash
uv run --with numpy --with scipy --with pillow python bench/landing_from_rec.py fin_kev_en_1 fin_laya_en_1
uv run --with numpy --with scipy --with pillow python bench/death_check.py fin_kev_en_1 fin_laya_en_1
```

## 4. 応答時間ベンチ(ゲームとは切り離す)

```bash
python3 bench/latency.py laya-ml_mps_mac http://127.0.0.1:8078/v1/systemone 300 20   # 開発中の状態文1,249件・日本語の11択
python3 bench/latency.py kev-4b_mlx_mac  http://127.0.0.1:8009/v1/systemone 300 20
node bench/eye.mjs 300                                                                 # 目(撮影＋判定の段階別)
bench/net.sh asia-northeast1-aiplatform.googleapis.com 50                              # ネットワークだけ
```

### Google Cloud(費用が出ます)

```bash
export PROJECT_ID=<検証用プロジェクト>
# Gemini(Vertex AI)。3.8 Flash は asia-northeast1 になく global のみ、思考は LOW が最小
PROJECT_ID=$PROJECT_ID PORT=8088 VERTEX_LOC=asia-northeast1 VERTEX_MODEL=gemini-2.5-flash uv run --with google-genai --with fastapi --with uvicorn servers/vertex_server.py
PROJECT_ID=$PROJECT_ID PORT=8089 VERTEX_LOC=global VERTEX_MODEL=gemini-3.8-flash VERTEX_THINK_LEVEL=LOW uv run --with google-genai --with fastapi --with uvicorn servers/vertex_server.py
python3 bench/latency.py gemini-2.5-flash_vertex_tokyo http://127.0.0.1:8088/v1/systemone 300 20
python3 bench/latency.py gemini-3.8-flash_vertex_global_low http://127.0.0.1:8089/v1/systemone 100 5

# kev-4b を Vertex AI のカスタム推論(L4)へ: イメージをビルド → デプロイ → 計測 → 撤去
gcloud artifacts repositories create owata --repository-format=docker --location=asia-northeast1 --project $PROJECT_ID
gcloud builds submit cloud --config cloud/cloudbuild.yaml --project $PROJECT_ID
mkdir -p logs
uv run --with google-cloud-aiplatform python cloud/gpu_endpoint.py deploy kev-l4-uscentral1 us-central1 g2-standard-8 NVIDIA_L4 > logs/deploy_kev-l4-uscentral1.log 2>&1 &
cloud/bench_kev_region.sh kev-l4-uscentral1 us-central1   # 結果は logs/bench_kev-l4-uscentral1.log。UNLINK_BILLING=1 なら最後に課金を外す
```

踏んだ落とし穴:

- カスタムコンテナのヘルス経路は、kev.serve に存在する `/v1/models` にする。存在しない `/health` にすると、デプロイが取り消せないまま課金が続いた
- python:slim ベースだと GPU ドライバが見えず、kev が黙って CPU で起動する。`LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib` などを渡す(`cloud/gpu_endpoint.py`)。起動ログの `on cuda` を必ず確認する
- 東京(asia-northeast1)の L4 推論は、プロジェクトによって枠が1しかなく、429(CustomModelServingL4GPUsPerProjectPerRegion)になることがある
- 撤去直後の一覧は、まだ削除の途中のことがある。課金を外す前に、endpoint と model が0になったことを確かめる

## 5. 文章の実験・目の精度・動画

```bash
python3 harness/probe_models.py      # 日本語(laya-ml と kev-4b を起動しておく)
python3 harness/probe_models2.py     # 呼び方と並び順の切り分け、向きの言い換え
python3 harness/probe_models_en.py   # 英語
uv run --with numpy --with scipy --with pillow python bench/eye_validate.py   # 自分で付けたラベルと録画で
python3 bench/platform_speed.py
TAG=fin_laya_en_1 MODEL_LABEL=laya-ml TITLE="laya-ml(英語)が人生オワタ2に挑む(100回)" \
  HL="63:初めて足場に乗った回,88:いちばん遠くまで行った回(x=312)" SPEED=10 OUT=fin_laya_en_1_montage.mp4 python3 viz/compose_montage.py
```

## 6. 第3部: 参考デモ方式のハーネス

物理の実測(`node harness/m_physics.mjs` → `data/controls/physics.json`)と、2つ目の罠の板のお手本(`perception/make_press_template.py <板が写ったコマ> 171 423`)を用意してから:

```bash
cd harness
env POLICY=systemone MODEL_URL=http://127.0.0.1:8009/v1/systemone TAG=demo_kev_rules EP=20 MAX_FRAMES=1500 GOAL_X=99999 REC=1 node run_demo.mjs   # JSON＋ルールの指示文＋質問3つ
env POLICY=labeled   MODEL_URL=http://127.0.0.1:8009/v1/systemone TAG=demo_kev_labeled EP=20 MAX_FRAMES=1500 GOAL_X=99999 REC=1 node run_demo.mjs   # 選択肢に判定(最初の版)
env POLICY=labeled2  MODEL_URL=http://127.0.0.1:8009/v1/systemone TAG=demo_kev_labeled2 EP=20 MAX_FRAMES=1500 GOAL_X=99999 REC=1 node run_demo.mjs  # 作り直した版
env POLICY=labeled2  MODEL_URL=http://127.0.0.1:8078/v1/systemone TAG=demo_laya_labeled2 EP=20 MAX_FRAMES=1500 GOAL_X=99999 REC=1 node run_demo.mjs
env POLICY=rules TAG=demo_rules_search EP=20 MAX_FRAMES=1500 GOAL_X=99999 REC=1 node run_demo.mjs                                            # ルールだけ
node sim_error.mjs demo_rules_search          # 物理の式の誤差(各判断から実際の操作列をなぞって比べる)
cd .. && python3 bench/demo_summary.py > data/DEMO_REPORT.md   # 第3部の表
python3 bench/label_reading.py                # モデルが SAFE/DEATH の判定を読めるか → data/label_reading.json
node bench/kev_prompt_length.mjs              # 指示文の長さと kev-4b の応答時間 → data/bench/kev_prompt_length.json
```

予測の不具合を直す前の値(記事の「5コマ先の高さの誤差 p90 17px→7px」)は、`harness/sim_error.mjs` の `s.zh = s0.trajectory.airborne_frames;` を `s.zh = Math.min(s0.trajectory.airborne_frames, PH.RISE_FRAMES - 1);` に戻すと出せます(記事の値は開発中のルールの試走で測ったもので、その試走のログはこのリポジトリに含めていません)。

```bash
```

動画: `TAG=demo_kev_labeled TITLE="..." HL="0:説明" SPEED=3 OUT=x.mp4 python3 viz/compose_demo.py`

# zenn-code

Zenn に書いた検証記事の、測定コードと生データです。記事の数字はここで再現できます。

記事本体: https://zenn.dev/ccie26302

## 収録

### `owata2-system1-realtime/` — 画面だけのJev互換AIに人生オワタ2は早かった

Jev と同じ `/v1/systemone` 形式で呼べる公開の判定モデル(kev-4b、laya-multilingual)に、『人生オワタの大冒険2』1面の最初の穴を、画面だけを見てゲームを止めずに遊ばせた一式と、応答時間のベンチマーク。ゲーム本体・ゲーム画面・録画は含めていません(作者の公式ページを開いて遊ぶ)。

- `harness/` — Playwright で公式ページを開き、時計を止めて1コマずつ進めるハーネス(`owata.mjs`)と試走(`run_play.mjs`)、操作の実測、文章の実験(`probe_models*.py`)、最終比較の一括実行(`chain_final.sh`)
- `perception/` — 目(ルールの画像処理、AI なし)のサーバと、お手本を自分の画面から作るスクリプト
- `bench/` — 応答時間(`latency.py`)、目(`eye.mjs`)、ネットワーク(`net.sh`)、録画からの足場判定、足場の速さ
- `cloud/` — kev-4b を Vertex AI のカスタム推論(L4)に置くコンテナとデプロイ・計測・撤去のスクリプト
- `servers/` — laya-ml と Gemini(Vertex AI)を `/v1/systemone` で呼べるようにする薄いサーバ
- `report.py` — 記事の表をすべて出す集計(出力は `data/REPORT.md`)
- `PREREGISTRATION.md` — 最終比較の事前登録
- `data/` — 試走ログ21本(`play/<TAG>/episodes.jsonl`、計1,820回)、ベンチの CSV、文章の実験、目の検証、操作の実測
- `REPRODUCE.md` — 再現手順

### `gemini-live-silence/` — 音声エージェントの沈黙を288試行で測った

Gemini Live API で音声エージェントを組み、ツール実行中に生じる無音を測った一式。

- `rig.py` — 測定リグ。体感の無音を再生カーソルで算出する `playout()` / `silence_in()` はここ
- `t36_thinking.py` / `t37_tools_rig.py` — 思考（180試行）/ ツール（108試行）の測定
- `t35_nb_generations.py` — 世代横断の `NON_BLOCKING` 確認
- `analyze.py` — 集計・効果量・検定（記事の全表を出力）
- `judge.py` — 前置き判定 / 音声適格性判定
- `data/` — 生データ（`e16_thinking.csv` 180行、`e17_tools.csv` 108行 ほか）
- `webapp/` — ブラウザから実際に話せるローカル版
- `REPRODUCE.md` — 再現手順

### `agent-injection/` — Gemini 5モデル1509試行、注入を防ぐのは手数だった

多段エージェントへの間接プロンプトインジェクションを、モデル横断で測った一式。凍結コーパスつき。

### `system-one-on-google-cloud/` — 文章を書かない Jev を Google Cloud で作れるか

選択肢から判定と確率だけを返す「System One」型の判定を、Vertex AI の3方式（enum 制約＋logprobs / 埋め込み＋分類器 / 言語化確信度）で作り、8,453試行で測った一式。

- `corpus.py` — 経費申請コーパス（テスト400 / 学習200、言い回しは学習とテストで分離）
- `harness.py` / `run.py` — 各方式の呼び出しと測定（精度・再試行・規程変更・再現性・速度・長い規程・思考の追加測定）
- `analyze.py` / `analyze_extra.py` — 事前登録どおりの主分析（自動化率・対数損失・ECE・ブートストラップ・McNemar）
- `report.py` — 記事の表をすべて出す集計（出力例は `data/report_final.txt`）
- `PLAN.md` — 測定前にコミットした事前登録と、追加測定の予測
- `data/` — 生データ（`acc.jsonl` 4,400行 ほか）
- `REPRODUCE.md` — 再現手順

### `tts-dialect-accent/` — Gemini 3.8 TTSの関西弁、エセかどうか測った

Gemini 3.8 Flash TTS の大阪ラベルの声に関西弁を読ませ、名詞のアクセント（高起・低起）を音の高さから判定した一式。Cloud Run ジョブ・Cloud Scheduler・Speech-to-Text（Chirp 3）・Cloud Text-to-Speech（Gemini-TTS 3.1）を使用。事前登録タグ `tts-prereg-1`〜`4`。

- `PLAN.md` — 事前登録（陰性ゲート後の判定方法の変更と、探索的な追加条件を含む）
- `synth.py` / `Dockerfile` — Cloud Run ジョブで回す合成（無料枠の1日上限で止まり翌日に続きから流す）
- `shape.py` / `report.py` / `extra.py` / `v31_report.py` — 判定と記事の表
- `q2.py` / `q2_report.py` / `q3.py` — お嬢様と関西弁、原稿との突き合わせ
- `data/` — 判定結果・書き起こし・聴き取りの回答（音声ファイルは含まない）
- `REPRODUCE.md` — 再現手順

### `gcp-leak-guard/` — 漏えい続発の今、Google Cloudの備えは効くか実測

個人情報保護委員会の注意喚起(9事例)とランサムへの備えを、Google Cloud の仕組みとして入れる `baseline.sh` と、効いているかを PASS / FAIL で確かめる `verify.sh`。組織のないプロジェクトでも動く。

- `baseline.sh` / `verify.sh` — 入れるスクリプトと確かめるスクリプト(step ごとに流せる)
- `dlp_mask.sh` — LLM に渡す前の文章から個人情報を伏せる
- `data/backup_trial.sh` — オーナー権限を取られた前提で、論理削除と、ロックした保持ポリシーのバケットを消しにいく
- `data/alert_trial.sh` / `alert_compute.py` — 監査ログのアラートが届くまでの時間(新しいインシデント)
- `data/` — 実測の結果(識別子は伏せた)
- `REPRODUCE.md` — 再現手順と片付け

## 使うにあたって

**API キーは各自でご用意ください。** このリポジトリに鍵は含まれていません。
実行すると、ご自身の Google AI Studio / Google Cloud の課金が発生します。

各ディレクトリの `REPRODUCE.md` に手順があります。seed を固定してあるので、
同じ順序で追試できます。

## ライセンス

MIT License

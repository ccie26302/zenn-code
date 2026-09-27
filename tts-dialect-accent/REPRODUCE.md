# 再現手順：Gemini 3.8 Flash TTS の関西弁アクセント

記事「Gemini 3.8 TTSの関西弁、エセかどうか測った」の測定一式です。事前登録はタグ `tts-prereg-1`（計画）、`tts-prereg-2`（陰性ゲート後の判定方法の変更）、`tts-prereg-3`（探索的な条件の追加）、`tts-prereg-4`（3.1 の拡張測定）。

## 環境

```bash
python3.13 -m venv .venv
.venv/bin/pip install "torch==2.8.*" "torchaudio==2.8.*" praat-parselmouth numpy scipy soundfile \
  google-genai==2.25.0 google-cloud-speech google-cloud-storage google-cloud-bigquery google-cloud-texttospeech
export PROJECT_ID=<あなたの Google Cloud プロジェクト ID>
export GEMINI_API_KEY=<AI Studio の API キー>       # 合成（synth.py）だけに使う
```

- 3.8 TTS は Gemini API の Interactions API で呼ぶ。google-genai 2.24.0 では `speech_metadata` が送れず 400 になるので 2.25.0 以上
- 無料枠は 3.8 Flash TTS で1日10リクエスト（測定時）。`synth.py auto` は上限に達したら終了し、次の実行で続きから流す

## 1. 合成（Cloud Run ジョブ、または手元）

```bash
python synth.py gate      # 陰性ゲート（東京3声×指示なし×標準の文）
python synth.py auto      # 本測定 → 探索条件 → 再現性 → お嬢様と関西弁
python vertex31.py        # 参考：Cloud Text-to-Speech の Gemini-TTS 3.1 Flash preview
```

Cloud Run ジョブで回すときは `GCS_BUCKET` と `BQ_TABLE` を設定し、API キーは Secret Manager から注入する（`Dockerfile` 参照）。BigQuery の記録は `sync_bq.py` で `data/requests.jsonl` に写す。

## 2. 解析

```bash
python report.py          # アクセントの判定と記事の表（結果1〜4、3.1 の比較、事前予測）→ data/report_q1.txt
python q2.py              # お嬢様と関西弁：各文の「わ」の測定 → data/q2_wa.csv
python q2_report.py       # 結果5の表と聴き分けの正解数 → data/report_q2.txt
python q2_global.py       # 結果5の探索：文章全体の長さと声の高さ
python extra.py           # 形の内訳・感度分析・再現性・位置など（探索、キャッシュのみで動く）
python vertex31x.py       # 3.1 の拡張測定（Cloud Text-to-Speech、6声×3条件×2回）
python v31_report.py      # 3.1 の節の表 → data/report_v31x.txt
python q3.py              # 原稿と書き起こしの突き合わせ（3.8）→ data/report_q3.txt
```

- 書き起こしは Speech-to-Text v2（Chirp 3、`us`）。60秒を超える音声は `stt.py` が分割する。結果は `data/stt/` に保存済み
- 拍の区間は torchaudio の MMS 強制アライメント、F0 は parselmouth
- 型の判定は `shape.py`。お手本（`data/templates_gate.json`）は陰性ゲートの実音声から作り、以後固定

## 注意

- 音声ファイル（WAV）はリポジトリに含めていません。`data/requests.jsonl` の原稿・声・指示・シードで再生成できますが、生成は確率的なので同じ音声にはなりません
- 聴き分けの回答（`data/listening_answers.json`）と、名詞の聴き取り確認（`data/check_answers.json`）は筆者1人のものです
- 実行すると Gemini API と Google Cloud（Speech-to-Text など）の課金が発生する場合があります

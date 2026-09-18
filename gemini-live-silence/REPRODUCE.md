# 再現手順

## 環境

```bash
python3.13 -m venv .venv
.venv/bin/pip install google-genai==2.24.0 numpy soundfile aiohttp
echo "<AI Studio の API キー>" > .aistudio.key && chmod 600 .aistudio.key
```

面は Gemini API（AI Studio）。Vertex AI では本記事の時点で `gemini-3.8-live` 系のセッションが張れません。

## 測定

```bash
# E1: 思考（180試行 / 5モデル×難易度2×問題3×6ブロック）
.venv/bin/python t36_thinking.py 6 20260918      # → data/e16_thinking.csv

# E2: ツール（108試行 / 2モデル×方式3×所要3水準×6ブロック）
.venv/bin/python t37_tools_rig.py 6 20260918     # → data/e17_tools.csv

# 世代横断の NON_BLOCKING 確認（各1試行）
.venv/bin/python t35_nb_generations.py           # → data/e15_nb_generations.csv
```

第1引数がブロック数、第2引数が seed。seed を固定すると条件の実行順が再現します。

## 集計

```bash
.venv/bin/python analyze.py    # E2の無音・確認的検定・効果量、E1のTTFA/到達率/HL差、失敗機構、Fisher/Wilson
.venv/bin/python judge.py      # 前置き判定 / 音声適格性判定
```

どちらもスクリプトの位置を基準に `data/` を読むので、どこから実行しても動きます。記事に載せた表はすべてこの2つで再現できます。

## 実機で試す

```bash
.venv/bin/python webapp/server.py     # http://localhost:8777
```

ブラウザから話しかけられます。モデル・`thinking_level`・ツールの返し方（blocking / nb_silent / nb_progress）・ツール所要を切り替えて比較できます。API キーはサーバ側に置き、ブラウザには出しません。

## 主要な指標の定義

- **体感の無音**: 音声チャンクの到着時刻ではなく、再生カーソルで算出（`rig.py` の `playout()` / `silence_in()`）。区間内に音が一切ない場合は区間全体を無音として返します
- **回答到達**: 発話の書き起こしに `正常` と `32` と `14` の3要素すべてを含むか（漢数字は正規化）
- **打ち切り**: ハードタイムアウト（E1 は35秒、E2 は45秒）。`censored=1` として記録し、全試行を1行ずつ CSV に残します

## 注意

- 全試行が同一ランです。条件はブロック内でシャッフルしていますが、時間帯交絡の解消はこのラン内に限られます
- 正常系のみです。ツールのエラー応答・引数不足は測っていません
- `analyze.py` はモデル名を厳密一致で照合します（部分一致だと `gemini-3.8-live` に `gemini-3.8-live-extended-thinking` が混入します）

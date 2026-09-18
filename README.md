# zenn-code

Zenn に書いた検証記事の、測定コードと生データです。記事の数字はここで再現できます。

記事本体: https://zenn.dev/ccie26302

## 収録

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

## 使うにあたって

**API キーは各自でご用意ください。** このリポジトリに鍵は含まれていません。
実行すると、ご自身の Google AI Studio / Google Cloud の課金が発生します。

各ディレクトリの `REPRODUCE.md` に手順があります。seed を固定してあるので、
同じ順序で追試できます。

## ライセンス

MIT License

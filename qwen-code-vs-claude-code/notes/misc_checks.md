# 記事に書いた細かい観察の出どころ(2026-10-19〜21)

- Ollama のメモリ: `ollama ps` で qwen3.8-27b-ctx64k が 17 GB、既定の qwen3.8:27b(文脈長 262144)が 18 GB(2026-10-19 の確認。会話の中で実行)
- 中継を止めた試験: 読者向けの settings.json と .env(接続先 http://127.0.0.1:8787/v1)を置き、中継を起動せずに `timeout 60 qwen -p "1+1は?"` を流すと、応答なしで「Operation cancelled.」で終わった(2026-10-19、1回)
- Node.js: `@qwen-code/qwen-code@0.25.2` の package.json の engines が `{"node": ">=22.0.0"}`
- Qwen Code の設定の頁(docs/users/configuration/settings.md、gh api で 2026-10-21 に取得): 181行 `privacy.usageStatisticsEnabled` 既定 `true`。859行 `QWEN_CODE_MODELS_DEV_REFRESH`「Set to off to stop the daily models.dev download」「On by default (24-hour interval)」「Project-level .env files and settings.json env cannot set this key」
- Agent Platform のアクセストークン: gcloud auth print-access-token のトークンの有効期間は1時間(Google の OAuth のアクセストークンの既定)。Qwen Code 0.25.2 の配布物で apiKeyHelper・apiKeyCommand・tokenCommand などの語を探し、見つからなかった
- 電気の目安単価 31円/kWh: 全国家庭電気製品公正取引協議会の新電力料金目安単価(税込)。日本照明工業会のガイド A139(2024)も同じ値を参照

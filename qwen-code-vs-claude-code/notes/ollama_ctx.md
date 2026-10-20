# Ollama の文脈長の確認(2026-10-19、Ollama 0.32.15、M4 Max 128GB)

- `ollama show qwen3.8:27b`: context length 262144、Q4_K_M
- 既定のまま読み込むと `ollama ps` の CONTEXT は 262144(このマシンでは、メモリが足りるので最大で読み込まれた)
- 約4.7万トークンの入力: 既定版も ctx64k 版も prompt_eval_count 47311 で、切り詰めは起きなかった。処理時間は 293 秒と 340 秒(読み込みを含む)
- つまり、この版・このマシンでは「既定だと文脈が足りない」は起きない。検証で 64k に固定したのは、メモリと速度を一定にするため
- 予備試行で Qwen Code の最初の要求は約1.5万トークン(中央値 15070〜15171)、1試行の最大は中央値 1.7万(Q)・2.3万(L)、最大 5.1万

# Qwen Code の外への通信(2026-10-19、0.25.2、Q の構成で「1+1 は?」を1回ずつ)

| 設定 | rum.aliyuncs.com(利用統計) | models.dev |
|---|---|---|
| 既定(#1、#2) | 2、2 | 1、1 |
| ~/.qwen/settings.json に {"privacy":{"usageStatisticsEnabled":false}}(#1、#2) | 0、0 | 0、0 |

本測定は既定の設定のまま流す(出口で止めて数える)。予備試行の43課題では、Q・L とも毎回 rum.aliyuncs.com への接続を試みた

訂正(同日): 上の表の「設定ありで 0、0」は誤り。設定ファイルを colima から見えない一時フォルダに置いたため、コンテナには空のフォルダとしてマウントされ、Qwen Code が設定を読めずに起動直後に止まっていた。/Users 以下に置き直して3回ずつ流し直した結果(どれも回答「2」を返した):

| 設定 | rum.aliyuncs.com | models.dev |
|---|---|---|
| 既定(3回) | 2、2、2 | 1、1、1 |
| privacy.usageStatisticsEnabled=false(3回) | 0、0、0 | 1、1、1 |
| 上の設定 + 環境変数 QWEN_CODE_MODELS_DEV=off(3回) | 0、0、0 | 0、0、0 |

models.dev はモデルの文脈長などの一覧(https://models.dev/api.json)。同梱の一覧(fetchedAt 2026-10-03)もあり、取得を止めても動いた

# 新しいプロジェクトからの呼び出し(2026-10-19)

- 新しいプロジェクトを作り、請求先をつなぎ、aiplatform.googleapis.com を有効にした直後に、オーナーのトークンで qwen/qwen3-coder-480b-a35b-instruct-maas を呼ぶと、2回とも 403(Permission 'aiplatform.endpoints.predict' denied ... (or it may not exist))
- 有効にしてから約3分後に、同じ呼び出しで応答「2」。Model Garden での有効化や規約への同意の操作は、していない
- 確かめたあとプロジェクトは削除した

# models.dev の取得だけを止める(2026-10-19、本測定とは別の試験用の中継で)

設計文書 docs/design/2026-08-23-models-dev-registry.md: `QWEN_CODE_MODELS_DEV=off` は一覧を使わず正規表現だけの判定に戻す。`QWEN_CODE_MODELS_DEV_REFRESH=off` は上流からの更新(取得)だけを止める。
利用者向けの文書 docs/users/features/goals.md: `privacy.usageStatisticsEnabled` は usage statistics を制御し、既定でオン。

| 設定(試験用の中継) | rum.aliyuncs.com | models.dev |
|---|---|---|
| 既定(対照、1回) | 2 | 1 |
| usageStatisticsEnabled=false(1回) | 0 | 1 |
| 上 + QWEN_CODE_MODELS_DEV_REFRESH=off(3回) | 0、0、0 | 0、0、0 |

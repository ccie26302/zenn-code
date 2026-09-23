# 再現手順：Jev の本質を Google Cloud で作って測る

## 環境

```bash
python3.13 -m venv .venv
.venv/bin/pip install google-genai==2.24.0 numpy scikit-learn==1.9.1
gcloud auth application-default login
export PROJECT_ID=<あなたのGoogle CloudプロジェクトID>
gcloud services enable aiplatform.googleapis.com --project=$PROJECT_ID
```

Vertex AI を使います（`global` エンドポイント）。`gemini-3.8-flash` は `global` にしかありません。

## 1. コーパスの生成

```bash
.venv/bin/python corpus.py
```

- テスト400件（各クラス100件）/ 学習200件
- 正解は規程から機械的に決まる（`truth()`）
- 言い回しは学習用とテスト用で分ける（`split_pools()`、共有ゼロ）
- 金額を読まない分類器の正答率（近道の下限）を `data/shortcut.json` に出す

seed を固定しているので、同じコーパスが再生成されます。

## 2. 測定

```bash
.venv/bin/python run.py acc      # 精度・確率の質（並列、リトライ有効）
.venv/bin/python run.py retry    # 感度分析: acc でエラーになった項目だけ再試行
.venv/bin/python run.py policy   # 規程を5万→3万円に変えたときの追従
.venv/bin/python run.py repeat   # 同一入力への再現性（5回ずつ）
.venv/bin/python run.py lat      # 速度（逐次、条件を交互配置、ウォームアップ除外、通信下限つき、リトライ無効）
.venv/bin/python run.py long     # 規程を約3,000トークンにしたときの速度
```

**速度の測定は、並列の測定がすべて終わってから実行してください。** 混雑が数字に混ざります。

## 3. 集計

```bash
.venv/bin/python analyze.py          # 正答率・自動化率・対数損失・ECE・校正・主比較
.venv/bin/python analyze_extra.py    # 速度・規程変更・再現性・長い規程・カスケード
```

## 事前登録

`PLAN.md` が測定前にコミットした検証計画です。予測は「何が起きたら外れか」を数値で書いています。

## 主要な定義

- **自動化率@誤り2%**: 確信度の高い順に採用し、採用分の誤り率が2%以下となる最大の採用率。**同じ確信度の項目はまとめて採否を決める**（全部100と答える方式を途中で切れないように）
- **エラーの扱い**: 主分析ではエラーを誤答・一様確率として数える。感度分析（`retry`）ではエラー項目を再試行した結果で置き換える
- **信頼区間**: 属性の組（用途区分・金額・領収書・承認）単位のクラスタブートストラップ 10,000回

## 注意

- API キーではなく ADC（`gcloud auth application-default login`）で認証します。リポジトリに認証情報は含まれていません
- 実行するとご自身の Google Cloud の課金が発生します。全測定で約6,400回の呼び出しです
- `gemini-2.5` 世代に依存しているため（logprobs を返すのが 2.5 のみ）、将来は再現できなくなる可能性があります

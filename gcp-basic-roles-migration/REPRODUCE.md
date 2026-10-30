# 再現手順

組織に属さないプロジェクトを1つ用意し、課金を付けてから流す。費用は無料枠の範囲に収まった(予算 1,000 円の通知は一度も来ていない)。

## 0. 準備

```bash
P=br-verify-$(date +%m%d%H%M)
gcloud projects create $P
gcloud billing projects link $P --billing-account=BILLING_ACCOUNT_ID
echo $P > project.txt
gcloud projects describe $P --format='value(projectNumber)' > project_number.txt
gcloud services enable iam.googleapis.com iamcredentials.googleapis.com cloudresourcemanager.googleapis.com \
  storage.googleapis.com bigquery.googleapis.com pubsub.googleapis.com secretmanager.googleapis.com \
  run.googleapis.com compute.googleapis.com cloudasset.googleapis.com policytroubleshooter.googleapis.com \
  logging.googleapis.com apikeys.googleapis.com --project=$P
```

ロールごとに SA を作り、自分にだけなりすましの権限を付ける。

```bash
ME=$(gcloud config get account)
for r in none viewer reader editor writer owner admin; do
  gcloud iam service-accounts create br-$r --project=$P
done
for r in viewer reader editor writer owner admin; do
  gcloud projects add-iam-policy-binding $P --member=serviceAccount:br-$r@$P.iam.gserviceaccount.com --role=roles/$r --condition=None
done
for r in none viewer reader editor writer owner admin; do
  gcloud iam service-accounts add-iam-policy-binding br-$r@$P.iam.gserviceaccount.com \
    --member=user:$ME --role=roles/iam.serviceAccountTokenCreator --project=$P
done
date -u +%Y-%m-%dT%H:%M:%SZ > data/sa_created_at.txt
```

## 1. ロール定義の揺れと差分

```bash
scripts/e0_sample.sh 50 30 day1      # 6ロール × 2経路 × 50回
python3 scripts/e1_diff.py day1      # data/e1_diff.csv, data/e1_dangerous.csv
```

## 2. 32の操作 × 8主体 × 3回

```bash
scripts/e3_prep.sh                   # 既定のバケット/データセットと、締め出したものを作る
./run.sh                             # SA を作ってから1時間待ち、伝播を確かめてから E3 を流す
python3 scripts/report.py            # 記事の表の数字
```

締め出したバケット(`-rfg`)の ACL に project owners が戻っていないかを、流す前に確かめること(本検証では1回戻った)。

## 3. 条件付きの付与

```bash
gcloud iam service-accounts create br-e4cond --project=$P   # トークン作成者の付与も同様に
python3 scripts/e4.py --label main          # 名前の条件3通り + 期限
python3 scripts/e4b.py                      # 逃がし方の書き方の比較、secrets.get
```

## 4. 置き換えと反映時間

```bash
gcloud iam service-accounts create br-e5swap --project=$P
python3 scripts/e5.py --label main          # 3方式 × 20回
python3 scripts/e5b.py                      # 付与/取り消しが効くまで(Pub/Sub)
python3 scripts/e5c.py                      # 同(Pub/Sub と Compute を同時に)
```

## 5. 洗い出しスクリプトの評価

```bash
SEED=$(python3 -c "import secrets;print(secrets.randbelow(10**6))")
python3 scripts/e6_plant.py $P $SEED c      # 中身は見ない。ハッシュだけ記録
python3 scripts/e6_find.py $P --json data/e6_find_eval_c.json
python3 scripts/e6_truth.py c
python3 scripts/e6_score.py c
```

## 片付け

```bash
gcloud projects delete $P
```

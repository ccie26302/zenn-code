# 再現手順

記事の数字は、組織のない個人のプロジェクト(asia-northeast1)と、使い捨てのプロジェクトで採りました。最終版の `baseline.sh` は、新規の空のプロジェクトで最初から流し、`verify.sh` が全部 PASS になることを確かめています(data/final_run.log、data/verify.txt)。それまでに3回失敗しています。作った直後の SA への付与が「存在しない」で止まった、実行中にスクリプトを書き換えて壊した、API を有効にした直後のリポジトリの作成が拒否された、の3つで、どれもスクリプトを直してから流し直しました(今のスクリプトは、反映待ちを少し待ってやり直します)。

## 0. 準備

```bash
export PROJECT_ID=<検証用のプロジェクト> BACKUP_PROJECT=<バックアップ用の別のプロジェクト> REGION=asia-northeast1
gcloud config set project $PROJECT_ID
```

`baseline.sh` は、両方のプロジェクトでオーナー相当の権限が要ります。`verify.sh` は、バックアップ側ではバケットの閲覧と、検証用のファイルを1つ置く書き込みの権限があれば動きます。gcloud は 587 以降で確かめています。スクリプトはこのフォルダ(gcp-leak-guard/)で実行してください。

## 1. 入れて、確かめる

```bash
GH_REPO=<owner/repo> BACKUP_RETENTION=600s LOCK_BACKUP=1 REMOVE_DEFAULT_EDITOR=1 ./baseline.sh
GH_REPO=<owner/repo> ./verify.sh
```

`verify.sh` は data/verify.txt と同じ行を出すはずです。注意が3つあります。

- `api: LB 経由の大量アクセスは 429` は、Cloud Armor のポリシーが効き始めるまで FAIL になることがあります(記事の1つ目の環境では、付けてから少なくとも6分は効いていませんでした)。数分おいて流し直してください
- アラートと WIF の行は、設定があるかの確認です。発火するかは 6. で、誤報が出ないかは 7. で確かめます
- バックアップの行は、`BACKUP_PROJECT` が別のプロジェクトで、保持ポリシーがロックされているときだけ PASS です。ロックしないで入れた場合は FAIL になります(ロックしていない保持ポリシーは解除できるため)

## 2. 脆弱性の件数(Dockerfile の4段階)

api/Dockerfile を次の4通りにして、それぞれビルドし、Artifact Registry に push します(`./baseline.sh patch` か `gcloud builds submit --tag ...`)。

1. `FROM python:3.12-slim` だけ
2. ＋ `RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*`
3. ＋ `pip install --no-cache-dir --upgrade pip`
4. ＋ `rm -f /usr/local/lib/python3.12/ensurepip/_bundled/pip-*.whl`(今の api/Dockerfile)

スキャンの結果は次で数えます。修正版のあるものは `fixAvailable` です。

```bash
gcloud artifacts docker images describe $REGION-docker.pkg.dev/$PROJECT_ID/apps/api:<tag> --show-package-vulnerability --format=json | python3 -c "
import json,sys,collections
v=json.load(sys.stdin).get('package_vulnerability_summary',{}).get('vulnerabilities',{})
print({s:len(i) for s,i in v.items()}, 'fixAvailable', sum(1 for i in v.values() for it in i if any(p.get('fixAvailable') for p in it['vulnerability']['packageIssue'])))"
```

結果は data/vuln_stages.txt です。件数はベースイメージの更新とスキャンのデータベースで日々変わります。

## 3. WIF

`./baseline.sh wif` が出す `workload_identity_provider` と `service_account` を、GitHub Actions のワークフローに書きます。

```yaml
on: [push, workflow_dispatch]
permissions:
  contents: read
  id-token: write
jobs:
  whoami:
    runs-on: ubuntu-latest
    steps:
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-pool/providers/github
          service_account: gh-deployer@<PROJECT_ID>.iam.gserviceaccount.com
      - uses: google-github-actions/setup-gcloud@v2
      - run: gcloud run services list --region asia-northeast1
```

main から実行すると成功し、別のブランチから実行するとトークンの交換で `unauthorized_client: The given credential is rejected by the attribute condition.` になります。権限を付けた直後は `iam.serviceAccounts.getAccessToken` が拒否されることがあり、数分後の再実行で通ります(data/wif.txt)。

## 4. DLP

```bash
echo '顧客情報: 山田太郎(taro@example.com, 090-1234-5678)、カード 4111 1111 1111 1111 で決済。この内容で返信文を作って。' > prompt.txt
./dlp_mask.sh < prompt.txt
CUSTOM=0 ./dlp_mask.sh < prompt.txt
```

組み込みの PHONE_NUMBER の確信度(単体と文の中)は data/dlp_likelihood.txt です。

## 5. バックアップを消しにいく(使い捨てのプロジェクトで)

```bash
SCRATCH_PROJECT=<使い捨てのプロジェクト> RET=600 ./data/backup_trial.sh   # TRY_PROJECT_DELETE=1 を付けると B6(プロジェクトの削除。lien で拒否されるはず)も試す
```

A(論理削除だけ)は、上書き・削除のあと戻せるか、論理削除を無効にされたら戻せるかを試します。B(保持ポリシー600秒をロック)は、削除・上書き・期間の短縮・解除・バケットの削除を試します。data/backup.txt の次の部分は、スクリプトではなく手で行いました。

- B1〜B5 の取り直し(1回目は出力の絞り込みの誤りで結果の行が消えた): 同じロック済みのバケットに、`gcloud storage rm`、上書きの `cp`、`buckets update --retention-period=1s`、`--clear-retention-period`、`storage rm -r` を順に実行
- A6〜A8(論理削除を有効に戻して復元): `gcloud storage buckets update gs://$SCRATCH_PROJECT-bk-softdelete --soft-delete-duration=7d` のあと、各世代を `gcloud storage restore gs://...#<generation>`
- B9〜B13(lien を外してのプロジェクト削除と取り消し):

```bash
L=$(gcloud alpha resource-manager liens list --project $SCRATCH_PROJECT --format='value(name)')
gcloud alpha resource-manager liens delete $L --project $SCRATCH_PROJECT   # オーナーは外せた
gcloud projects delete $SCRATCH_PROJECT                                   # 消せた
gcloud projects undelete $SCRATCH_PROJECT                                 # 取り消し。課金の紐付けは外れるので付け直す
```

バックアップに書き込みだけを許した SA の試験(data/backup.txt の末尾)は、本番側のプロジェクトに SA を作り、バックアップのバケットに `roles/storage.objectCreator` を付けて、なりすましで `gcloud storage cp`(拒否された)と JSON API への直接アップロード(新規は 200、上書き・読み取り・削除は 403)を試しました。

## 6. アラートが届くまでの時間(検証用のプロジェクトで)

通知は試験専用の購読(security-alerts-trial)で受けます。

api を一瞬 allUsers に公開し、IAM チェックの設定を切り替えます。鍵を作って消すための SA(権限なし)を先に作ります。

```bash
gcloud iam service-accounts create leak-test
./data/alert_trial.sh create 1     # 試行用のポリシーを作る
# 15分以上待つ(作った直後のポリシーは効かないことがあった。data/alert_notes.txt)
./data/alert_trial.sh run 1        # 操作して、監査ログの時刻から通知の publishTime までを測る
```

結果は data/alerts.csv に追記されます。試行ごとに別のポリシーを作るので、どれも新しいインシデントの最初の通知を測ります。次の回のポリシーは、前の回が終わってから作ってください(先に作ると前の回の操作で発火し、測れなくなります)。記事の秒数は、識別子を除いた公開データから `python3 data/alert_compute.py` で出し直せます。data/alerts_reopened_incidents.csv は、開いたままのインシデントへの再通知を測ってしまった旧版のデータです(記事では使っていません)。

## 7. 誤報が出ないか(週次の再デプロイ)

```bash
./data/fp_check.sh   # A: 週次ジョブを動かして6分待つ(鳴らないはず)、B: 人の手で IAM チェックを外す(鳴るはず)
```

結果は data/fp_check.txt です。旧版のフィルタで週次ジョブを動かしたときの誤報は data/fp_weekly.txt です。最初の直し方(patch-runner を一律に除く)では、オーナーが patch-runner になりすまして IAM チェックを外すとすり抜けました(fp_check.txt の D)。今のフィルタで、なりすましは鳴り、週次ジョブは鳴らないことは次で確かめます(SA のなりすまし権限 `roles/iam.serviceAccountTokenCreator` を一時的に自分に付けて流し、終わったら外す)。

```bash
./data/fp_check2.sh   # E: なりすましで IAM チェックを外す(鳴るはず)、F: 5分半おいて週次ジョブ(鳴らないはず)
```

## 8. 片付け(課金を止める)

```bash
g() { gcloud --project $PROJECT_ID --quiet "$@"; }
g compute forwarding-rules delete api-fr --global
g compute target-http-proxies delete api-proxy
g compute url-maps delete api-map
g compute backend-services delete api-be --global
g compute network-endpoint-groups delete api-neg --region $REGION
g compute security-policies delete api-armor
g run services delete app --region $REGION
g run services delete api --region $REGION
g scheduler jobs delete weekly-patch --location $REGION
g artifacts repositories delete apps --location $REGION
g artifacts repositories delete cloud-run-source-deploy --location $REGION
g storage rm -r gs://$PROJECT_ID-build-src gs://$PROJECT_ID-personal-data gs://run-sources-$PROJECT_ID-$REGION
g storage rm -r gs://${PROJECT_ID}_cloudbuild   # gcloud builds submit を使った場合に自動で作られる
g storage rm -r gs://$PROJECT_ID-alert-test   # 6. を試した場合
for p in $(g monitoring policies list --format='value(name)' --filter='displayName="SA key created" OR displayName="Public grant (allUsers/allAuthenticatedUsers)" OR displayName="Cloud Run invoker IAM check disabled"'); do g monitoring policies delete $p; done
for c in $(g beta monitoring channels list --filter='displayName="security-alerts"' --format='value(name)'); do g beta monitoring channels delete $c; done
g pubsub subscriptions delete security-alerts-sub; g pubsub topics delete security-alerts
g secrets delete app-db-password; g secrets delete other-team-key
g iam workload-identity-pools delete github-pool --location=global   # プールは30日間、論理削除の状態で残る
g pubsub subscriptions delete security-alerts-trial   # 6. を試した場合
for s in app-runtime api-runtime app-builder patch-runner gh-deployer leak-test backup-writer; do g iam service-accounts delete $s@$PROJECT_ID.iam.gserviceaccount.com; done
# バックアップのバケットは、保持期間が過ぎるまで消せない。ロックしていればプロジェクトに lien も付いている(バケットを消しても残る)
gcloud --project $BACKUP_PROJECT storage rm -r gs://$BACKUP_PROJECT-backup
```

検証のためだけのプロジェクトなら、プロジェクトごと消すのが確実です(`gcloud projects delete $PROJECT_ID`)。ロックしたバケットがあったプロジェクトは、保持期間が過ぎてバケットを消しても lien が残りました(1分後も残っていた)。プロジェクトを消すには、lien を外します。

```bash
L=$(gcloud alpha resource-manager liens list --project $BACKUP_PROJECT --format='value(name)')
gcloud alpha resource-manager liens delete $L --project $BACKUP_PROJECT
gcloud projects delete $BACKUP_PROJECT
```

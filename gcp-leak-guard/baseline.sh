#!/bin/bash
# Google Cloud で漏えいに備える仕組みを、1つのプロジェクトに入れるスクリプト(組織なしでも動く版)。
# usage: PROJECT_ID=xxx REGION=asia-northeast1 GH_REPO=owner/repo [BACKUP_PROJECT=yyy LOCK_BACKUP=1] ./baseline.sh [step ...]   (step 省略時は全部)
# 各 step は何度流しても同じ状態になるように書いている(すでにあればスキップ)。
set -euo pipefail
: "${PROJECT_ID:?PROJECT_ID を設定してください}"
REGION=${REGION:-asia-northeast1}
GH_REPO=${GH_REPO:-}                       # WIF を使う GitHub リポジトリ(owner/name)。空なら wif をスキップ
HERE=$(cd "$(dirname "$0")" && pwd)
g() { gcloud --project "$PROJECT_ID" --quiet "$@"; }
# 作った直後の SA は、IAM の付与で「存在しない」と言われることがある(反映待ち)。付与は少し待ってやり直す
retry() { for i in 1 2 3 4 5 6 7 8 9 10; do "$@" && return 0; echo "retry $i: $1 $2 $3" >&2; sleep 10; done; return 1; }
ensure() { g $1 >/dev/null 2>&1 || g $2 >/dev/null; }   # $1 = 確かめるコマンド、$2 = 無ければ作るコマンド(空白を含む引数は使わない)
PNUM=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
RUN_SA=app-runtime@$PROJECT_ID.iam.gserviceaccount.com
BUILD_SA=app-builder@$PROJECT_ID.iam.gserviceaccount.com   # ソースからのデプロイのビルド専用(既定の Compute SA を使わない)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

step_apis() {
  g services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
    containerscanning.googleapis.com cloudscheduler.googleapis.com secretmanager.googleapis.com \
    logging.googleapis.com monitoring.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
    dlp.googleapis.com
  default_sa_check
}

# Compute Engine API を有効にすると、既定の Compute SA ができ、組織のないプロジェクトでは Editor が自動で付く。
# ソースからのデプロイのビルドも、指定しなければこの SA で動く。REMOVE_DEFAULT_EDITOR=1 で Editor を外す
# (既存のワークロードがこの SA に頼っていないか確かめてから)
default_sa_check() {
  local SA="$PNUM-compute@developer.gserviceaccount.com"
  g projects get-iam-policy "$PROJECT_ID" --flatten='bindings[].members' \
    --filter="bindings.role=roles/editor AND bindings.members=serviceAccount:$SA" --format='value(bindings.role)' | grep -q . || return 0
  if [ "${REMOVE_DEFAULT_EDITOR:-0}" = 1 ]; then
    retry g projects remove-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA" --role=roles/editor --condition=None >/dev/null
    echo "既定の Compute SA から Editor を外した"
  else echo "注意: 既定の Compute SA に Editor が付いている(REMOVE_DEFAULT_EDITOR=1 で外す)" >&2; fi
}

# 事例3・5: 実行用の SA を専用に作り、読める secret を1つだけにする(既定の Compute SA を使わない)
step_runtime() {
  g iam service-accounts describe "$RUN_SA" >/dev/null 2>&1 || \
    g iam service-accounts create app-runtime --display-name="Cloud Run runtime (least privilege)"
  for s in app-db-password other-team-key; do
    g secrets describe "$s" >/dev/null 2>&1 || \
      printf 'dummy-%s-%s' "$s" "$(openssl rand -hex 8)" | g secrets create "$s" --data-file=- --replication-policy=automatic
  done
  # 読めるのは app-db-password だけ。プロジェクト全体ではなく secret 単位で付ける
  retry g secrets add-iam-policy-binding app-db-password \
    --member="serviceAccount:$RUN_SA" --role=roles/secretmanager.secretAccessor >/dev/null
}

# 事例1・2: ソースからデプロイし、ベースイメージ(OS・言語ランタイム)の自動更新を有効にする。
# 認証必須(--no-allow-unauthenticated)。secret は環境変数に値を書かず、実行時に API で読む
step_app() {
  # ビルド用の SA には、ソースの置き場所の読み取り、イメージの置き場所への書き込み、ログの書き込みだけを付ける
  g iam service-accounts describe "$BUILD_SA" >/dev/null 2>&1 || g iam service-accounts create app-builder --display-name="source deploy build"
  local SRC=gs://run-sources-$PROJECT_ID-$REGION
  retry ensure "storage buckets describe $SRC" "storage buckets create $SRC --location $REGION --uniform-bucket-level-access --public-access-prevention"
  # API を有効にした直後は作成が拒否されることがある。1回目が裏で成功していても二重に作らないよう、確認と作成をまとめてやり直す
  retry ensure "artifacts repositories describe cloud-run-source-deploy --location $REGION" \
    "artifacts repositories create cloud-run-source-deploy --repository-format=docker --location $REGION"
  retry g storage buckets add-iam-policy-binding "$SRC" --member="serviceAccount:$BUILD_SA" --role=roles/storage.objectViewer >/dev/null
  retry g artifacts repositories add-iam-policy-binding cloud-run-source-deploy --location "$REGION" --member="serviceAccount:$BUILD_SA" --role=roles/artifactregistry.writer >/dev/null
  retry g projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$BUILD_SA" --role=roles/logging.logWriter --condition=None >/dev/null
  g run deploy app --source "$HERE/app" --region "$REGION" \
    --build-service-account "projects/$PROJECT_ID/serviceAccounts/$BUILD_SA" \
    --base-image python312 --automatic-updates \
    --service-account "$RUN_SA" --no-allow-unauthenticated \
    --set-env-vars GOOGLE_CLOUD_PROJECT="$PROJECT_ID" --max-instances 2
}

# 事例1・2: Dockerfile のサービスは、週次で再ビルド(--pull で最新のベースを取る)→ 再デプロイ → 古いイメージを掃除。
# Artifact Registry は push 時に脆弱性スキャン(Container Scanning API)。古いイメージは cleanup policy で自動削除
AR=$REGION-docker.pkg.dev/$PROJECT_ID/apps
PATCH_SA=patch-runner@$PROJECT_ID.iam.gserviceaccount.com
API_SA=api-runtime@$PROJECT_ID.iam.gserviceaccount.com   # 公開する API は、何の権限も持たない SA で動かす
step_registry() {
  retry ensure "artifacts repositories describe apps --location $REGION" \
    "artifacts repositories create apps --repository-format=docker --location $REGION --description=scanned-app-images"
  cat > $TMP/cleanup-policy.json <<'JSON'
[
  {"name": "keep-latest-5", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 5}},
  {"name": "delete-older-than-30d", "action": {"type": "Delete"}, "condition": {"tagState": "ANY", "olderThan": "30d"}}
]
JSON
  g artifacts repositories set-cleanup-policies apps --location "$REGION" --policy=$TMP/cleanup-policy.json --no-dry-run >/dev/null
}

step_patch() {
  # ソースは Cloud Storage に置き、Cloud Build が毎週それを再ビルドする
  BKT=gs://$PROJECT_ID-build-src
  g storage buckets describe "$BKT" >/dev/null 2>&1 || g storage buckets create "$BKT" --location "$REGION" --uniform-bucket-level-access --public-access-prevention
  tar -czf $TMP/api-src.tgz -C "$HERE/api" . && g storage cp $TMP/api-src.tgz "$BKT/api-src.tgz" >/dev/null
  cat > $TMP/patch-build.json <<JSON
{
  "source": {"storageSource": {"bucket": "$PROJECT_ID-build-src", "object": "api-src.tgz"}},
  "steps": [
    {"name": "gcr.io/cloud-builders/docker", "args": ["build", "--pull", "--no-cache", "-t", "$AR/api:weekly-\$BUILD_ID", "-t", "$AR/api:latest", "."]},
    {"name": "gcr.io/cloud-builders/docker", "args": ["push", "--all-tags", "$AR/api"]},
    {"name": "gcr.io/google.com/cloudsdktool/cloud-sdk:slim", "entrypoint": "gcloud",
     "args": ["run", "deploy", "api", "--image", "$AR/api:weekly-\$BUILD_ID", "--region", "$REGION",
              "--service-account", "$API_SA", "--ingress", "internal-and-cloud-load-balancing", "--quiet"]}
  ],
  "serviceAccount": "projects/$PROJECT_ID/serviceAccounts/$PATCH_SA",
  "options": {"logging": "CLOUD_LOGGING_ONLY"}
}
JSON
  g iam service-accounts describe "$PATCH_SA" >/dev/null 2>&1 || g iam service-accounts create patch-runner --display-name="weekly rebuild and redeploy"
  g iam service-accounts describe "$API_SA" >/dev/null 2>&1 || g iam service-accounts create api-runtime --display-name="public API runtime (no permissions)"
  # 権限は必要な範囲だけに付ける。プロジェクト全体にはビルドの作成とログの書き込みだけ。
  # ソースの読み取りはそのバケットだけ、イメージの書き込みはそのリポジトリだけ、デプロイは api だけ
  for r in roles/cloudbuild.builds.editor roles/logging.logWriter; do
    retry g projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$PATCH_SA" --role="$r" --condition=None >/dev/null
  done
  for r in roles/cloudbuild.builds.builder roles/artifactregistry.writer roles/storage.objectViewer; do   # 旧版で付けていた広い権限を外す
    g projects remove-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$PATCH_SA" --role="$r" --condition=None >/dev/null 2>&1 || true
  done
  retry g storage buckets add-iam-policy-binding "$BKT" --member="serviceAccount:$PATCH_SA" --role=roles/storage.objectViewer >/dev/null
  retry g artifacts repositories add-iam-policy-binding apps --location "$REGION" --member="serviceAccount:$PATCH_SA" --role=roles/artifactregistry.writer >/dev/null
  retry g iam service-accounts add-iam-policy-binding "$API_SA" --member="serviceAccount:$PATCH_SA" --role=roles/iam.serviceAccountUser >/dev/null
  retry g iam service-accounts add-iam-policy-binding "$PATCH_SA" --member="serviceAccount:$PATCH_SA" --role=roles/iam.serviceAccountUser >/dev/null
  # api がまだ無いときだけ、作るためにプロジェクト単位の run.developer を一時的に付ける(作ったあとで api 単位に付け替える)
  g run services describe api --region "$REGION" >/dev/null 2>&1 || \
    retry g projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$PATCH_SA" --role=roles/run.developer --condition=None >/dev/null
  # 毎週月曜 3:00(日本時間)に Cloud Build を起動する。起動は PATCH_SA の OAuth トークンで行う(鍵なし)
  g scheduler jobs describe weekly-patch --location "$REGION" >/dev/null 2>&1 && g scheduler jobs delete weekly-patch --location "$REGION" >/dev/null
  g scheduler jobs create http weekly-patch --location "$REGION" --schedule="0 3 * * 1" --time-zone="Asia/Tokyo" \
    --uri="https://cloudbuild.googleapis.com/v1/projects/$PROJECT_ID/locations/$REGION/builds" --http-method=POST \
    --headers=Content-Type=application/json --message-body-from-file=$TMP/patch-build.json \
    --oauth-service-account-email="$PATCH_SA" --oauth-token-scope=https://www.googleapis.com/auth/cloud-platform >/dev/null
  # 初回は api がまだ無いので、ジョブを1回手で動かし、デプロイされるまで待つ(以降は毎週自動)
  if ! g run services describe api --region "$REGION" >/dev/null 2>&1; then
    g scheduler jobs run weekly-patch --location "$REGION"
    for i in $(seq 1 60); do g run services describe api --region "$REGION" >/dev/null 2>&1 && break; sleep 20; done
    g run services describe api --region "$REGION" --format='value(status.url)'
  fi
  retry g run services add-iam-policy-binding api --region "$REGION" --member="serviceAccount:$PATCH_SA" --role=roles/run.developer >/dev/null
  g projects remove-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$PATCH_SA" --role=roles/run.developer --condition=None >/dev/null 2>&1 || true
}

# 事例6・不要データの消去・ランサムへの備え: 個人データを置くバケットは
#   公開を防ぐ(public access prevention)、ACL を使わない(均一なアクセス)、
#   消されても戻せる(論理削除 7日)、目的を終えたら消える(作成から N 日で自動削除)
DATA_RETENTION_DAYS=${DATA_RETENTION_DAYS:-30}
step_data() {
  BKT=gs://$PROJECT_ID-personal-data
  g storage buckets describe "$BKT" >/dev/null 2>&1 || \
    g storage buckets create "$BKT" --location "$REGION" --uniform-bucket-level-access --public-access-prevention \
      --soft-delete-duration=7d
  cat > $TMP/lifecycle.json <<JSON
{"rule": [{"action": {"type": "Delete"}, "condition": {"age": $DATA_RETENTION_DAYS}}]}
JSON
  g storage buckets update "$BKT" --lifecycle-file=$TMP/lifecycle.json --soft-delete-duration=7d >/dev/null
}

# 事例4・8(ランサム): バックアップは「別のプロジェクト」に「消せない形」で置く。
#   保持ポリシー(BACKUP_RETENTION)の間は、オーナーでもオブジェクトの削除・上書きができない。
#   LOCK_BACKUP=1 でロックすると、期間の短縮・ポリシーの解除・バケットの削除もできなくなる。ロックは元に戻せない。
#   gcloud storage buckets update --lock-retention-period は確認を求め、--quiet だと中断されてロックされない。ここでは API で直接ロックし、isLocked を確かめる。
#   同じプロジェクトのオーナーは lien を外してプロジェクトごと消せるので、BACKUP_PROJECT は管理者の違う別プロジェクトにする(同じなら作らない)
step_backup() {
  if [ -z "${BACKUP_PROJECT:-}" ] || [ "$BACKUP_PROJECT" = "$PROJECT_ID" ]; then
    echo "BACKUP_PROJECT(本番とは別のプロジェクト)が未指定なのでスキップ"; return 0; fi
  if [ "${LOCK_BACKUP:-0}" = 1 ] && [ -z "${BACKUP_RETENTION:-}" ]; then
    echo "LOCK_BACKUP=1 では BACKUP_RETENTION(例: 7d、試すなら 600s)を明示してください。ロックは元に戻せません" >&2; return 1; fi
  RET=${BACKUP_RETENTION:-7d}; BK=gs://$BACKUP_PROJECT-backup
  b() { gcloud --project "$BACKUP_PROJECT" --quiet "$@"; }
  b storage buckets describe "$BK" >/dev/null 2>&1 || \
    b storage buckets create "$BK" --location "$REGION" --uniform-bucket-level-access \
      --public-access-prevention --soft-delete-duration=7d --retention-period="$RET"
  # すでにあるバケットの保持期間が指定より短ければ延ばす(ロック後も延ばすことはできる。短くはできない)
  local want cur; want=$(python3 -c "import sys;v=sys.argv[1];u={'s':1,'m':60,'h':3600,'d':86400}[v[-1]];print(int(v[:-1])*u)" "$RET" 2>/dev/null) || {
    echo "BACKUP_RETENTION は 600s / 30m / 12h / 7d の形で指定してください(年は 365d のように日で)" >&2; return 1; }
  cur=$(b storage buckets describe "$BK" --format='value(retention_policy.retentionPeriod)')
  if [ -z "$cur" ]; then b storage buckets update "$BK" --retention-period="$RET" >/dev/null; echo "保持ポリシーが無かったので $RET を付けた"
  elif [ "$cur" -lt "$want" ]; then b storage buckets update "$BK" --retention-period="$RET" >/dev/null; echo "保持期間を ${cur}s から $RET に延ばした"
  elif [ "$cur" -gt "$want" ]; then echo "注意: 保持期間はすでに ${cur}s で、$RET より長い(ロック済みなら短くできない)" >&2; fi
  if [ "${LOCK_BACKUP:-0}" = 1 ]; then
    MG=$(b storage buckets describe "$BK" --format='value(metageneration)')
    curl -sS -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
      "https://storage.googleapis.com/storage/v1/b/${BK#gs://}/lockRetentionPolicy?ifMetagenerationMatch=$MG" >/dev/null
    b storage buckets describe "$BK" --format='value(retention_policy.isLocked)' | grep -q True || { echo "ロックできていません" >&2; return 1; }
  fi
  b storage buckets describe "$BK" --format='value(retention_policy)'
}

# 早期の検知: 「鍵が作られた」「誰でもアクセスできる権限(allUsers / allAuthenticatedUsers)が付いた」を、
# 監査ログ(管理アクティビティ、既定で有効・無料)から即アラートにする。通知先は Pub/Sub(メール等に置き換え可)
ALERT_TOPIC=security-alerts
step_detect() {
  g pubsub topics describe "$ALERT_TOPIC" >/dev/null 2>&1 || g pubsub topics create "$ALERT_TOPIC" >/dev/null
  g pubsub subscriptions describe "$ALERT_TOPIC-sub" >/dev/null 2>&1 || g pubsub subscriptions create "$ALERT_TOPIC-sub" --topic "$ALERT_TOPIC" >/dev/null
  # Cloud Monitoring のサービスエージェント(初回は作成が要る)に、このトピックへの publish だけを許す
  g beta services identity create --service=monitoring.googleapis.com >/dev/null 2>&1 || true
  retry g pubsub topics add-iam-policy-binding "$ALERT_TOPIC" \
    --member="serviceAccount:service-$PNUM@gcp-sa-monitoring-notification.iam.gserviceaccount.com" --role=roles/pubsub.publisher >/dev/null
  CH=$(g beta monitoring channels list --filter='displayName="security-alerts"' --format='value(name)' | head -1)
  [ -n "$CH" ] || CH=$(g beta monitoring channels create --display-name=security-alerts --type=pubsub \
    --channel-labels=topic=projects/$PROJECT_ID/topics/$ALERT_TOPIC --format='value(name)')
  mkpolicy() {  # $1=表示名 $2=ログのフィルタ
    local EXIST; EXIST=$(g monitoring policies list --filter="displayName=\"$1\"" --format='value(name)' | head -1)
    python3 - "$1" "$2" "$CH" > $TMP/policy.json <<'PY'
import json, sys
name, flt, ch = sys.argv[1:4]
print(json.dumps({
  "displayName": name, "combiner": "OR",
  "conditions": [{"displayName": name, "conditionMatchedLog": {"filter": flt}}],
  "alertStrategy": {"notificationRateLimit": {"period": "300s"}, "autoClose": "1800s"},
  "notificationChannels": [ch],
  "documentation": {"content": "監査ログに一致しました。意図した操作か確認してください。", "mimeType": "text/markdown"}}))
PY
    # 同じ名前のポリシーがあれば、中身(フィルタなど)を今の版に更新する(旧版のフィルタが残らないように)
    if [ -n "$EXIST" ]; then g monitoring policies update "$EXIST" --policy-from-file=$TMP/policy.json >/dev/null
    else g monitoring policies create --policy-from-file=$TMP/policy.json >/dev/null; fi
  }
  mkpolicy "SA key created" 'logName:"cloudaudit.googleapis.com%2Factivity" AND protoPayload.methodName="google.iam.admin.v1.CreateServiceAccountKey"'
  # 「無効のまま更新した」ときにも一致するので、毎週の再デプロイ(patch-runner)は除く。ALERT_EXCLUDE_SA に、自分の CI の SA を空白区切りで足せる。
  # 除くのは「その SA が直接動いたとき」だけ。人がその SA になりすました操作(serviceAccountDelegationInfo がある)は除かない。
  # 限界: その SA として動くビルドを作れる人(ビルドの作成と、その SA の actAs を持つ人)は、検知をすり抜けられる
  local EXC=""
  for sa in $PATCH_SA ${ALERT_EXCLUDE_SA:-}; do
    EXC="$EXC AND NOT (protoPayload.authenticationInfo.principalEmail=\"$sa\" AND NOT protoPayload.authenticationInfo.serviceAccountDelegationInfo:*)"
  done
  mkpolicy "Cloud Run invoker IAM check disabled" 'logName:"cloudaudit.googleapis.com%2Factivity" AND protoPayload.serviceName="run.googleapis.com" AND (protoPayload.request.service.invokerIamDisabled=true OR protoPayload.request.service.metadata.annotations."run.googleapis.com/invoker-iam-disabled"="true")'"$EXC"
  # Cloud Run やプロジェクトは SetIamPolicy、Cloud Storage のバケットは storage.setIamPermissions。付与(ADD)の差分か、新しいポリシーに allUsers / allAuthenticatedUsers があれば通知
  mkpolicy "Public grant (allUsers/allAuthenticatedUsers)" 'logName:"cloudaudit.googleapis.com%2Factivity" AND (protoPayload.methodName:"SetIamPolicy" OR protoPayload.methodName="storage.setIamPermissions") AND ((protoPayload.serviceData.policyDelta.bindingDeltas.action="ADD" AND (protoPayload.serviceData.policyDelta.bindingDeltas.member:"allUsers" OR protoPayload.serviceData.policyDelta.bindingDeltas.member:"allAuthenticatedUsers")) OR protoPayload.request.policy.bindings.members:"allUsers" OR protoPayload.request.policy.bindings.members:"allAuthenticatedUsers")'
}

# 事例3(不正ログイン)・認証情報の漏えい: CI に長期の鍵を置かない。GitHub Actions は OIDC で短期トークンに交換する(WIF)。
# 条件で「このリポジトリの main ブランチ」だけに絞る。条件を書かないと、同じプロバイダを使う他のリポジトリやブランチからも借りられる
step_wif() {
  [ -n "$GH_REPO" ] || { echo "GH_REPO が空なのでスキップ"; return 0; }
  POOL=github-pool; PROV=github; DEPLOY_SA=gh-deployer@$PROJECT_ID.iam.gserviceaccount.com
  g iam workload-identity-pools describe $POOL --location=global >/dev/null 2>&1 || \
    g iam workload-identity-pools create $POOL --location=global --display-name="GitHub Actions"
  g iam workload-identity-pools providers describe $PROV --location=global --workload-identity-pool=$POOL >/dev/null 2>&1 || \
    g iam workload-identity-pools providers create-oidc $PROV --location=global --workload-identity-pool=$POOL \
      --issuer-uri="https://token.actions.githubusercontent.com" \
      --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
      --attribute-condition="assertion.repository=='$GH_REPO' && assertion.ref=='refs/heads/main'"
  g iam service-accounts describe "$DEPLOY_SA" >/dev/null 2>&1 || g iam service-accounts create gh-deployer --display-name="GitHub Actions (main only)"
  retry g projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$DEPLOY_SA" --role=roles/run.viewer --condition=None >/dev/null
  retry g iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --role=roles/iam.workloadIdentityUser \
    --member="principalSet://iam.googleapis.com/projects/$PNUM/locations/global/workloadIdentityPools/$POOL/attribute.repository/$GH_REPO" >/dev/null
  echo "workload_identity_provider: projects/$PNUM/locations/global/workloadIdentityPools/$POOL/providers/$PROV"
  echo "service_account: $DEPLOY_SA"
}

# 事例9(API の悪用): API はロードバランサ＋Cloud Armor の後ろに置き、IP ごとのレートリミットで大量アクセスを 429 にする。
# Cloud Run は ingress を「内部と LB のみ」にして、run.app の URL からは直接届かないようにする。
# LB 経由の公開では Cloud Run の呼び出し元 IAM チェックを外す(--no-invoker-iam-check)。これは allUsers の付与とは別の
# 「公開」なので、step_detect のアラートでこの変更も検知する
RATE_LIMIT=${RATE_LIMIT:-30}           # 1 IP あたり 60 秒間のリクエスト数の上限
step_armor() {
  g services enable compute.googleapis.com
  default_sa_check
  [ -n "${SKIP_RUN_UPDATE:-}" ] || g run services update api --region "$REGION" --ingress internal-and-cloud-load-balancing --no-invoker-iam-check >/dev/null
  g compute network-endpoint-groups describe api-neg --region "$REGION" >/dev/null 2>&1 || \
    g compute network-endpoint-groups create api-neg --region "$REGION" --network-endpoint-type=serverless --cloud-run-service=api
  g compute security-policies describe api-armor >/dev/null 2>&1 || {
    g compute security-policies create api-armor --description="rate limit per IP"
    g compute security-policies rules create 1000 --security-policy api-armor --expression="true" \
      --action=throttle --rate-limit-threshold-count="$RATE_LIMIT" --rate-limit-threshold-interval-sec=60 \
      --conform-action=allow --exceed-action=deny-429 --enforce-on-key=IP
  }
  g compute backend-services describe api-be --global >/dev/null 2>&1 || {
    g compute backend-services create api-be --global --load-balancing-scheme=EXTERNAL_MANAGED
    g compute backend-services update api-be --global --security-policy api-armor
    g compute backend-services add-backend api-be --global --network-endpoint-group=api-neg --network-endpoint-group-region="$REGION"
  }
  g compute url-maps describe api-map >/dev/null 2>&1 || g compute url-maps create api-map --default-service api-be
  # 検証のため HTTP(80)。本番はドメインと証明書を用意し、target-https-proxies と 443 で公開する
  g compute target-http-proxies describe api-proxy >/dev/null 2>&1 || g compute target-http-proxies create api-proxy --url-map api-map
  g compute forwarding-rules describe api-fr --global >/dev/null 2>&1 || \
    g compute forwarding-rules create api-fr --global --load-balancing-scheme=EXTERNAL_MANAGED --target-http-proxy api-proxy --ports 80
  echo "LB IP: $(g compute forwarding-rules describe api-fr --global --format='value(IPAddress)')"
}

all="apis runtime app registry patch data backup detect wif armor"
for s in ${@:-$all}; do echo "== $s"; "step_$s"; done

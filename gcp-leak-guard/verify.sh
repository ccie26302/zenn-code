#!/bin/bash
# baseline.sh で入れた仕組みが「効いているか」を確かめる。各項目を PASS / FAIL で出す。
# 読み取りと、すぐ元に戻す操作が中心。例外は2つ: 論理削除の確認で小さなファイルを作って消して戻す、
# バックアップの確認で verify/ の下に小さなファイルを1つ置く(保持期間が過ぎるまで消せない。同じ名前なので増えない)。
# usage: PROJECT_ID=xxx BACKUP_PROJECT=yyy REGION=asia-northeast1 ./verify.sh
set -uo pipefail
TMPE=$(mktemp); trap 'rm -f "$TMPE"' EXIT
: "${PROJECT_ID:?}"; REGION=${REGION:-asia-northeast1}
g() { gcloud --project "$PROJECT_ID" --quiet "$@"; }
ok() { echo "PASS  $1"; }; ng() { echo "FAIL  $1"; FAILED=1; }; FAILED=0
APP=$(g run services describe app --region "$REGION" --format='value(status.url)')
TOK=$(gcloud auth print-identity-token)

# 公開しない: トークンなしは 403
[ "$(curl -s -o /dev/null -w '%{http_code}' "$APP/")" = 403 ] && ok "app: トークンなしは 403" || ng "app: トークンなしで届く"
# 最小権限: 自分の secret は読める、他チームの secret は読めない
curl -s -H "Authorization: Bearer $TOK" "$APP/secret/app-db-password" | grep -q '"readable":true' && ok "app: 自分の secret は読める" || ng "app: 自分の secret が読めない"
curl -s -H "Authorization: Bearer $TOK" "$APP/secret/other-team-key" | grep -q '"error":"PermissionDenied"' && ok "app: 他の secret は PermissionDenied" || ng "app: 他の secret が読める(または別の理由で失敗)"
# 脆弱性: ベースイメージの自動更新
g run services describe app --region "$REGION" --format=json | grep -q 'linux-base-image-update' && ok "app: ベースイメージの自動更新が有効" || ng "app: 自動更新が無効"
# 脆弱性: 修正版がある脆弱性が 0
FIX=$(g artifacts docker images describe "$REGION-docker.pkg.dev/$PROJECT_ID/apps/api:latest" --show-package-vulnerability --format=json 2>/dev/null | python3 -c "
import json,sys
v=json.load(sys.stdin).get('package_vulnerability_summary',{}).get('vulnerabilities',{})
print(sum(1 for items in v.values() for it in items if any(p.get('fixAvailable') for p in it.get('vulnerability',{}).get('packageIssue',[]))))")
[ "$FIX" = 0 ] && ok "api: 修正版がある脆弱性は 0" || ng "api: 修正版がある脆弱性が $FIX 件"
g scheduler jobs describe weekly-patch --location "$REGION" --format='value(state)' | grep -q ENABLED && ok "週次パッチのジョブが有効" || ng "週次パッチのジョブがない"
# 個人データのバケット: 公開できない、論理削除から戻せる
BKT=gs://$PROJECT_ID-personal-data
# 設定が enforced のときだけ、実際に allUsers を付けにいって拒否されることを確かめる(設定が無いバケットを一瞬でも公開しないため)
if [ "$(g storage buckets describe "$BKT" --format='value(public_access_prevention)' 2>/dev/null)" = enforced ]; then
  if g storage buckets add-iam-policy-binding "$BKT" --member=allUsers --role=roles/storage.objectViewer >/dev/null 2>&1; then
    ng "バケットを公開できてしまう"; g storage buckets remove-iam-policy-binding "$BKT" --member=allUsers --role=roles/storage.objectViewer >/dev/null 2>&1
  else ok "バケットは公開できない(public access prevention)"; fi
else ng "個人データのバケットに public access prevention が無い"; fi
echo "verify $(date +%s)" | g storage cp - "$BKT/verify.txt" >/dev/null 2>&1; g storage rm "$BKT/verify.txt" >/dev/null 2>&1
DEL=$(g storage ls --soft-deleted "$BKT/verify.txt" 2>/dev/null | tail -1)   # gs://.../verify.txt#<generation>
[ -n "$DEL" ] && g storage restore "$DEL" >/dev/null 2>&1 && g storage cat "$BKT/verify.txt" | grep -q verify && ok "消したファイルを論理削除から戻せる" || ng "論理削除から戻せない"
g storage rm "$BKT/verify.txt" >/dev/null 2>&1
# ランサム: バックアップは別のプロジェクトに、保持ポリシーをロックして置く。オーナーでも消せないことを確かめる
BACKUP_PROJECT=${BACKUP_PROJECT:-}; BK=gs://$BACKUP_PROJECT-backup
if [ -z "$BACKUP_PROJECT" ] || [ "$BACKUP_PROJECT" = "$PROJECT_ID" ]; then ng "バックアップが別のプロジェクトにない(BACKUP_PROJECT を指定)"
else
  RP=$(gcloud --project "$BACKUP_PROJECT" storage buckets describe "$BK" --format='value(retention_policy.retentionPeriod,retention_policy.isLocked)' 2>"$TMPE"); RC=$?
  if [ $RC -ne 0 ] && grep -q -E '403|does not have|PERMISSION' "$TMPE"; then ng "バックアップ側を確認できない(このアカウントに閲覧の権限が無い)"
  elif [ $RC -ne 0 ]; then ng "バックアップのバケットが無い"
  elif [ -z "$RP" ]; then ng "バックアップのバケットに保持ポリシーがない"
  else
    echo "verify" | gcloud --project "$BACKUP_PROJECT" storage cp - "$BK/verify/verify.txt" >/dev/null 2>&1   # 2回目以降は上書きが拒否されるが、ファイルは残っている
    if ! gcloud --project "$BACKUP_PROJECT" storage ls "$BK/verify/verify.txt" >/dev/null 2>&1; then ng "バックアップのバケットに書けない"
    elif gcloud --project "$BACKUP_PROJECT" storage rm "$BK/verify/verify.txt" >/dev/null 2>&1; then ng "バックアップを消せてしまう"
    elif echo "$RP" | grep -q True; then ok "バックアップは別のプロジェクトにあり、消せず、保持ポリシーはロック済み"
      curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" "https://cloudresourcemanager.googleapis.com/v3/liens?parent=projects/$BACKUP_PROJECT" | grep -q '"origin": "storage.googleapis.com"' \
        || echo "注意  バックアップ側のプロジェクトに lien が無い(または確認できない。プロジェクトごと消せる)"
      own() { gcloud projects get-iam-policy "$1" --flatten='bindings[].members' --filter='bindings.role=roles/owner' --format='value(bindings.members)' | sort; }
      [ -n "$(comm -12 <(own "$PROJECT_ID") <(own "$BACKUP_PROJECT"))" ] && echo "注意  本番とバックアップ側に同じオーナーがいる(その人が乗っ取られると両方消せる)"
    else ng "バックアップは消せないが、保持ポリシーがロックされていない(解除すれば消せる)"; fi
  fi
fi
# 検知: アラートポリシーがある
POL=$(g monitoring policies list --format=json)
for n in "SA key created" "Public grant (allUsers/allAuthenticatedUsers)" "Cloud Run invoker IAM check disabled"; do
  echo "$POL" | python3 -c "
import json,sys; n=sys.argv[1]
p=[x for x in json.load(sys.stdin) if x['displayName']==n]
f=p[0]['conditions'][0]['conditionMatchedLog']['filter'] if len(p)==1 else ''
ok=len(p)==1 and p[0].get('enabled') and len(p[0].get('notificationChannels',[]))>0 \
   and ('storage.setIamPermissions' in f or not n.startswith('Public')) and ('serviceAccountDelegationInfo' in f or not n.startswith('Cloud Run'))
sys.exit(0 if ok else 1)" "$n" && ok "検知のアラート「$n」が有効で通知先がある(設定の確認。発火は data/alert_trial.sh で確かめる)" || ng "検知のアラート「$n」が無い、無効、通知先が無い、または古いフィルタ"
done
# 鍵を持たない: WIF の条件にリポジトリとブランチが入っている
COND=$(g iam workload-identity-pools providers describe github --location=global --workload-identity-pool=github-pool --format='value(attributeCondition)' 2>/dev/null)
if [ -n "${GH_REPO:-}" ]; then
  [ "$COND" = "assertion.repository=='$GH_REPO' && assertion.ref=='refs/heads/main'" ] && ok "WIF の条件が $GH_REPO の main だけに限定されている" || ng "WIF の条件が期待と違う: $COND"
else
  echo "$COND" | grep -q "assertion.repository==" && echo "$COND" | grep -q "assertion.ref==" && ok "WIF の条件でリポジトリとブランチを限定(GH_REPO を渡すと完全一致で確かめる)" || ng "WIF の条件が緩い: $COND"
fi
# 権限: 週次ビルドの SA にプロジェクト全体の広い権限が無い。既定の Compute SA に Editor が無い
IAMP=$(g projects get-iam-policy "$PROJECT_ID" --format=json) || { ng "プロジェクトの IAM を読めない"; IAMP='{"bindings":[]}'; }
roles_of() { echo "$IAMP" | python3 -c "import json,sys;m=sys.argv[1];print(' '.join(sorted(b['role'] for b in json.load(sys.stdin).get('bindings',[]) if m in b['members']))+' ')" "$1"; }
PR=$(roles_of "serviceAccount:patch-runner@$PROJECT_ID.iam.gserviceaccount.com")
[ "$PR" = "roles/cloudbuild.builds.editor roles/logging.logWriter " ] && ok "週次ビルドの SA はプロジェクト全体にはビルドの作成とログの書き込みだけ" || ng "週次ビルドの SA の権限が広い: $PR"
PNUM=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
roles_of "serviceAccount:$PNUM-compute@developer.gserviceaccount.com" | grep -q 'roles/editor' && ng "既定の Compute SA に Editor が付いている" || ok "既定の Compute SA に Editor が無い"
# SA を指定しないビルドは既定のビルド用 SA で動く。旧 Cloud Build SA(<番号>@cloudbuild)が既定だと、ビルドを作れる人はその広い権限を使える
g builds get-default-service-account --format='value(serviceAccountEmail)' 2>/dev/null | grep -q '@cloudbuild.gserviceaccount.com' && echo "注意  既定のビルド用 SA が旧 Cloud Build SA。ビルドを作れる SA(patch-runner)から、その権限に届きうる"
# API: run.app には直接届かず、LB 経由では大量アクセスが 429 になる
API=$(g run services describe api --region "$REGION" --format='value(status.url)')
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$API/items/00000000-0000-0000-0000-000000000000")
[ -n "$API" ] && [ "$CODE" = 404 ] && ok "api: インターネットから run.app の URL には届かない(404)" || ng "api: run.app の応答が $CODE"
IP=$(g compute forwarding-rules describe api-fr --global --format='value(IPAddress)' 2>/dev/null)
if [ -z "$IP" ]; then ng "api: ロードバランサがない"; else
  codes=$(for i in $(seq 1 60); do curl -s -m 5 -o /dev/null -w '%{http_code}\n' "http://$IP/items/00000000-0000-0000-0000-000000000000"; done | sort | uniq -c | tr '\n' ' ')
  if echo "$codes" | grep -q ' 429'; then ok "api: LB 経由の大量アクセスは 429($codes)"
  elif ! echo "$codes" | grep -q ' 200'; then ng "api: ロードバランサがまだ応答しない($codes。作った直後は数分かかる)"
  else ng "api: 429 にならない($codes。Cloud Armor が効き始めるまで数分かかることがある)"; fi
fi
exit $FAILED

#!/bin/bash
# ランサムを想定し、プロジェクトのオーナー権限を取られた前提で、バックアップを消せるかを試す。
#   A: 論理削除だけのバケット … 上書き(暗号化の代わり)・削除のあと戻せるか。論理削除を無効にされたら、すでに消されたものは戻せるか
#   B: 保持ポリシーをロックしたバケット … 削除・上書き・保持期間の短縮・ポリシーの解除・バケットの削除ができるか
# usage: SCRATCH_PROJECT=<使い捨てのプロジェクト> ./data/backup_trial.sh   (本番の PROJECT_ID と取り違えないよう、変数名を分けている)
#   必ず使い捨てのプロジェクトで。B はロックするので、保持期間(RET 秒)が過ぎるまでバケットを消せない。
#   B6(プロジェクトの削除)は TRY_PROJECT_DELETE=1 のときだけ試す。ロックが効いていれば lien で拒否される。
#   lien を外してのプロジェクト削除と取り消し(data/backup.txt の B9〜B13)は、このスクリプトではなく手で行った
P=${SCRATCH_PROJECT:?使い捨てのプロジェクトを SCRATCH_PROJECT に指定}; R=${REGION:-asia-northeast1}; RET=${RET:-600}
g() { gcloud --project "$P" --quiet "$@"; }
try() { local label=$1; shift; if out=$("$@" 2>&1); then echo "$label | OK"; else echo "$label | DENIED | $(echo "$out" | grep -m1 -E 'ERROR' | cut -c1-240)"; fi; }

A=gs://$P-bk-softdelete; B=gs://$P-bk-locked
echo "## A: soft delete only ($A)"
g storage buckets create $A --location $R --uniform-bucket-level-access --public-access-prevention --soft-delete-duration=7d >/dev/null
echo "original" | g storage cp - $A/db.dump >/dev/null
echo "ENCRYPTED-BY-RANSOMWARE" | g storage cp - $A/db.dump >/dev/null        # 上書き
OLD=$(g storage ls --soft-deleted $A/db.dump | head -1)
echo "overwritten; soft-deleted generation: ${OLD##*#}"
try "A1 restore original after overwrite" g storage restore "$OLD"
echo "A1 content now: $(g storage cat $A/db.dump 2>&1 | head -1)"
g storage rm $A/db.dump >/dev/null 2>&1                                      # 削除
GENS=$(g storage ls --soft-deleted $A/db.dump 2>/dev/null)
echo "A2 soft-deleted generations after rm: $(echo "$GENS" | grep -c .)"
try "A3 attacker disables soft delete (--clear-soft-delete)" g storage buckets update $A --clear-soft-delete
sleep 60
echo "A4 soft-deleted entries listed after disable (60s): $(g storage ls --soft-deleted $A/db.dump 2>/dev/null | grep -c .)"
for u in $GENS; do try "A5 restore ${u##*#} by explicit generation" g storage restore "$u"; done
echo "## B: retention policy locked, ${RET}s ($B)"
g storage buckets create $B --location $R --uniform-bucket-level-access --public-access-prevention --retention-period=${RET}s >/dev/null
echo "backup $(date +%s)" | g storage cp - $B/db.dump >/dev/null
# 注意: gcloud storage buckets update --lock-retention-period は確認を求める。--quiet を付けると「中断」になり、ロックされない(1回目の試行はこれで失敗した)
MG=$(g storage buckets describe $B --format='value(metageneration)')
curl -s -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://storage.googleapis.com/storage/v1/b/${B#gs://}/lockRetentionPolicy?ifMetagenerationMatch=$MG" >/dev/null
LOCKED=$(curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" "https://storage.googleapis.com/storage/v1/b/${B#gs://}?fields=retentionPolicy" | python3 -c "import json,sys; print(json.load(sys.stdin)['retentionPolicy'])")
echo "retentionPolicy: $LOCKED"
echo "$LOCKED" | grep -q "'isLocked': True" || { echo "NOT LOCKED. stop"; exit 1; }
try "B1 delete object" g storage rm $B/db.dump
try "B2 overwrite object" bash -c "echo ENCRYPTED | gcloud --project $P --quiet storage cp - $B/db.dump"
try "B3 shorten retention to 1s" g storage buckets update $B --retention-period=1s
try "B4 clear retention policy" g storage buckets update $B --clear-retention-period
try "B5 delete bucket" g storage rm -r $B
[ "${TRY_PROJECT_DELETE:-0}" = 1 ] && try "B6 delete project (lien should block)" gcloud projects delete $P --quiet
echo "B7 liens: $(gcloud alpha resource-manager liens list --project $P --format='value(origin,reason)' 2>&1 | tr '\n' ' ')"
echo "B8 content: $(g storage cat $B/db.dump 2>&1 | head -1)"

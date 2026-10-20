#!/bin/bash
# 使い捨てのプロジェクトの基準を取る(snapshot)/ 基準との差分を消して戻す(restore)。手元のオーナーの権限で動かす
# usage: gcp_state.sh snapshot DIR | restore DIR | diff DIR
export CLOUDSDK_CORE_DISABLE_PROMPTS=1; exec </dev/null
set -u; cd "$(dirname "$0")"; P=$(cat target_project.txt); R=asia-northeast1; D=$2; mkdir -p $D
snap(){ local o=$1
  gcloud projects get-iam-policy $P --format=json > $o/iam.json
  gcloud storage buckets list --project $P --format='value(name)' | sort > $o/buckets
  gcloud iam service-accounts list --project $P --format='value(email)' | sort > $o/sas
  gcloud run services list --project $P --region $R --format='value(metadata.name)' | sort > $o/run
  gcloud run jobs list --project $P --region $R --format='value(metadata.name)' 2>/dev/null | sort > $o/jobs
  gcloud services list --enabled --project $P --format='value(config.name)' | sort > $o/apis
  gcloud iam service-accounts get-iam-policy qwen-run-rt@$P.iam.gserviceaccount.com --project $P --format=json > $o/runrt_iam.json
}
case $1 in
  snapshot) snap $D ;;
  diff) mkdir -p $D/now; snap $D/now; for f in buckets sas run jobs apis; do comm -13 $D/$f $D/now/$f | sed "s/^/+$f /"; comm -23 $D/$f $D/now/$f | sed "s/^/-$f /"; done
        python3 -c "
import json,sys
a=json.load(open('$D/iam.json')); b=json.load(open('$D/now/iam.json'))
f=lambda p: sorted((x['role'],m) for x in p.get('bindings',[]) for m in x.get('members',[]))
A,B=set(f(a)),set(f(b)); [print('+iam',*x) for x in sorted(B-A)]; [print('-iam',*x) for x in sorted(A-B)]" ;;
  restore) mkdir -p $D/now; snap $D/now
    for b in $(comm -13 $D/buckets $D/now/buckets); do gcloud storage rm -r --all-versions "gs://$b" -q >/dev/null 2>&1; gcloud storage buckets delete "gs://$b" -q >/dev/null 2>&1; echo "deleted bucket $b"; done
    for s in $(comm -13 $D/run $D/now/run); do gcloud run services delete $s --project $P --region $R -q >/dev/null 2>&1; echo "deleted run $s"; done
    for s in $(comm -13 $D/jobs $D/now/jobs); do gcloud run jobs delete $s --project $P --region $R -q >/dev/null 2>&1; echo "deleted job $s"; done
    for s in $(comm -13 $D/sas $D/now/sas); do gcloud iam service-accounts delete $s --project $P -q >/dev/null 2>&1; echo "deleted sa $s"; done
    for a in $(comm -13 $D/apis $D/now/apis); do gcloud services disable $a --project $P --force -q >/dev/null 2>&1; echo "disabled api $a"; done
    for a in $(comm -23 $D/apis $D/now/apis); do gcloud services enable $a --project $P -q >/dev/null 2>&1; echo "enabled api $a"
      # API を無効にすると Google 管理のサービスエージェントが消え、IAM に deleted: が残る。作り直してから IAM を戻す
      gcloud beta services identity create --service=$a --project $P -q >/dev/null 2>&1; sleep 20; done
    # 有効に戻した直後はサービスエージェントの作り直しが終わっておらず、IAM に deleted: が残ることがある(予備試行のあとの妥当性確認の G06 で起きた)。
    # 残っていたら作り直しを頼んでから IAM を戻す。IAM の戻しは成功するまでやり直す
    if grep -q '"deleted:serviceAccount:service-' $D/now/iam.json; then
      gcloud beta services identity create --service=run.googleapis.com --project $P -q >/dev/null 2>&1; echo "recreated run service agent"; sleep 30
    fi
    python3 - $D <<'PY'
import json, subprocess, sys, time
D = sys.argv[1]
for f, cmd in (("iam.json", ["gcloud", "projects", "set-iam-policy", open("target_project.txt").read().strip()]),
               ("runrt_iam.json", ["gcloud", "iam", "service-accounts", "set-iam-policy", "qwen-run-rt@%s.iam.gserviceaccount.com" % open("target_project.txt").read().strip()])):
    base = json.load(open(D + "/" + f)); now = json.load(open(D + "/now/" + f))
    key = lambda p: sorted((x["role"], tuple(sorted(x.get("members", [])))) for x in p.get("bindings", []))
    if key(base) != key(now):
        base["etag"] = now.get("etag", base.get("etag")); json.dump(base, open(D + "/_restore.json", "w"))
        for k in range(5):
            if k: time.sleep(20); base["etag"] = json.loads(subprocess.run((["gcloud", "projects", "get-iam-policy", cmd[-1]] if "projects" in cmd else ["gcloud", "iam", "service-accounts", "get-iam-policy", cmd[-1], "--project", open("target_project.txt").read().strip()]) + ["--format=json"], capture_output=True, text=True).stdout)["etag"]; json.dump(base, open(D + "/_restore.json", "w"))
            r = subprocess.run(cmd + [D + "/_restore.json", "--format=none", "-q"] + (["--project", open("target_project.txt").read().strip()] if "service-accounts" in cmd else []), capture_output=True, text=True)
            print("restored", f, "try", k + 1, r.returncode, r.stderr.strip()[-200:])
            if r.returncode == 0: break
PY
    ;;
esac

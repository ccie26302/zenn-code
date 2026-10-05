#!/bin/bash
# 自分の2つのプロジェクト(A・B)で、独自URL を A が削除したあと、B が同じ名前を作成できるかを1回だけ確かめ、
# 削除からの経過秒と URL の応答を記録する(取得を繰り返し試す処理は入れていない)。
# usage: ./measure_release.sh NAME PROJECT_A PROJECT_B TRIAL   (NAME は A ですでに作成済みで、svc-alpha を返していること)
set -u
N=$1; PA=$2; PB=$3; T=$4; OUT=data/release.csv; R=asia-northeast1
[ -f $OUT ] || echo "trial,name,t_sec,event,detail" > $OUT
now() { python3 -c 'import time;print(f"{time.time():.3f}")'; }
probe() { local b; b=$(curl -s -m 5 -w ' HTTP%{http_code}' https://$N.cloud.run/); echo "$(echo "$b" | grep -o -E 'svc-(alpha|bravo)' | head -1 || true)$(echo "$b" | grep -o 'HTTP[0-9]*' | tail -1)"; }
T0=$(now); log() { echo "$T,$N,$(python3 -c "print(round($(now)-$T0,1))"),$1,$2" | tee -a $OUT; }
log before "$(probe)"
gcloud beta run domain-mappings delete --domain=$N.cloud.run --region=$R --project $PA --quiet >/dev/null 2>&1; log deleted_by_A "rc=$?"
if gcloud beta run domain-mappings create --service=svc-bravo --domain=$N.cloud.run --region=$R --project $PB >/dev/null 2>&1; then log created_by_B ok; else log create_by_B_failed ng; exit 0; fi
for i in $(seq 1 30); do p=$(probe); log probe "$p"; [ "$p" = "svc-bravoHTTP200" ] && { log serves_B "$p"; break; }; sleep 2; done

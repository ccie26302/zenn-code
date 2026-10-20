#!/bin/bash
# なりすましのトークンを発行し、.new に書いてから mv で差し替える(フォルダごとマウントしているので、コンテナから新しい値が見える)
cd "$(dirname "$0")"; umask 077; C=<model-project>
one(){ local sa=$1 dir=$2 f=$3; for i in $(seq 1 30); do gcloud auth print-access-token --impersonate-service-account=$sa@$C.iam.gserviceaccount.com 2>/dev/null > secrets/$dir/$f.new && [ -s secrets/$dir/$f.new ] && mv secrets/$dir/$f.new secrets/$dir/$f && return 0; sleep 20; done; return 1; }
while true; do
  one qwen-model model model_token && one qwen-agent agent token && one qwen-judge judge token
  [ "$1" = once ] && exit 0
  sleep 1500
done

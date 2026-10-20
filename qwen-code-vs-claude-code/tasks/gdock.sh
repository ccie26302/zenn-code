#!/bin/bash
# Google Cloud の課題の実行。usage: gdock.sh MODE TASK WORK ID
#  setup   : 初期状態を作る(オーナーのトークン、直接のネットワーク)
#  agent:X : X.sh(solve / nearmiss / alt)をエージェントと同じ条件で流す(--internal、中継、dummy トークン)
#  judge   : 判定(qwen-judge のトークン、直接のネットワーク、/work は読み取り専用)
set -u; export CLOUDSDK_CORE_DISABLE_PROMPTS=1
MODE=$1; T=$2; W=$3; ID=$4
TR="$(cd "$(dirname "$0")" && pwd)"; H="$TR/../harness"; P=$(cat $H/target_project.txt)
COMMON=(-e TARGET_PROJECT=$P -e P=$P -e ID=$ID -e CLOUDSDK_CORE_PROJECT=$P -e GOOGLE_PROJECT=$P -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0='*' -v "$TR:/tasks:ro")
case $MODE in
  setup)
    umask 077; mkdir -p $H/secrets/owner; gcloud auth print-access-token > $H/secrets/owner/token
    docker run --rm --network bridge "${COMMON[@]}" -e CLOUDSDK_AUTH_ACCESS_TOKEN_FILE=/owner/token -e OWNER_TOKEN_FILE=/owner/token \
      -v "$H/secrets/owner:/owner:ro" -v "$W:/work" qwen-agent bash -c "cd /work && export GOOGLE_OAUTH_ACCESS_TOKEN=\$(cat /owner/token) && bash /tasks/$T/setup.sh"
    rc=$?; : > $H/secrets/owner/token; exit $rc ;;
  agent:*)
    S=${MODE#agent:}; echo gcp > $H/ctl/egress_mode; rm -f $H/ctl/no_enable
    [ -f "$TR/$T/no_enable" ] && [ "$S" != judge_exec ] && touch $H/ctl/no_enable
    docker run --rm --network qwen-int "${COMMON[@]}" -e HTTPS_PROXY=http://proxy:3128 -e HTTP_PROXY=http://proxy:3128 -e NO_PROXY=proxy,collector \
      -e CLOUDSDK_CORE_CUSTOM_CA_CERTS_FILE=/ca/bundle.pem -e SSL_CERT_FILE=/ca/bundle.pem -e REQUESTS_CA_BUNDLE=/ca/bundle.pem \
      -e GOOGLE_APPLICATION_CREDENTIALS=/cred/sa.json \
      -v "$H/ca:/ca:ro" -v "$H/cred/fake_sa.json:/cred/sa.json:ro" -v "$W:/work" qwen-agent bash -c "gcloud auth activate-service-account --key-file=/cred/sa.json -q >/dev/null 2>&1; cd /work && bash /tasks/$T/$S.sh"
    rc=$?; echo none > $H/ctl/egress_mode; rm -f $H/ctl/no_enable; exit $rc ;;
  judge)
    docker run --rm --network bridge "${COMMON[@]}" -e CLOUDSDK_AUTH_ACCESS_TOKEN_FILE=/judge/token -e JUDGE_TOKEN_FILE=/judge/token \
      -e CLOUDSDK_BILLING_QUOTA_PROJECT=$P -v "$H/secrets/judge:/judge:ro" -v "$W:/work:ro" qwen-agent python3 /tasks/$T/judge.py /work ;;
esac

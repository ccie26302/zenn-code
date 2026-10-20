#!/bin/bash
# 負の対照を、エージェントと同じコンテナの設定・同じ出口で流す。usage: negcontrol_run.sh 出力のCSV
cd "$(dirname "$0")"; P=$(cat target_project.txt)
echo gcp > ctl/egress_mode; rm -f ctl/no_enable ctl/claude
docker run --rm --network qwen-int --cap-drop ALL --security-opt no-new-privileges --pids-limit 1024 --memory 8g \
  -e HTTPS_PROXY=http://proxy:3128 -e NO_PROXY=proxy,collector,localhost \
  -e SSL_CERT_FILE=/ca/bundle.pem -e REQUESTS_CA_BUNDLE=/ca/bundle.pem -e NODE_EXTRA_CA_CERTS=/ca/bundle.pem \
  -e CLOUDSDK_CORE_CUSTOM_CA_CERTS_FILE=/ca/bundle.pem -e GOOGLE_APPLICATION_CREDENTIALS=/cred/sa.json \
  -e CLOUDSDK_CORE_PROJECT=$P -e CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
  -v "$PWD/ca:/ca:ro" -v "$PWD/cred/fake_sa.json:/cred/sa.json:ro" -v "$PWD/negcontrol.sh:/negcontrol.sh:ro" \
  --entrypoint bash qwen-agent -c "gcloud auth activate-service-account --key-file=/cred/sa.json -q >/dev/null 2>&1; bash /negcontrol.sh $P" > "$1"
echo none > ctl/egress_mode
awk -F, 'NR>1{n++; if($1==$2) m++} END{print m"/"n" が期待どおり"}' "$1"

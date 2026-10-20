#!/bin/bash
# 中継を立ち上げる。agent は --internal ネットワークだけにつなぐ
set -e; cd "$(dirname "$0")"; umask 077
C=<model-project>; P=$(cat target_project.txt); PN=$(gcloud projects describe $P --format='value(projectNumber)')
./refresh_tokens.sh once
docker network inspect qwen-int >/dev/null 2>&1 || docker network create --internal qwen-int >/dev/null
docker rm -f qwen-proxy >/dev/null 2>&1 || true
docker run -d --name qwen-proxy --network bridge -e ALLOW_MODELS="${ALLOW_MODELS-}" -e MODEL_PROJECT=$C \
  -e TARGET_PROJECT=$P -e TARGET_NUMBER=$PN \
  -v "$PWD/secrets/model:/secrets/model:ro" -v "$PWD/secrets/agent:/secrets/agent:ro" -v "$PWD/secrets/claude:/secrets/claude:ro" -v "$PWD/ctl:/ctl:ro" \
  -v "$PWD/mitm:/mitm" -v "$PWD/logs:/logs" qwen-proxy >/dev/null
docker network connect --alias proxy --alias collector qwen-int qwen-proxy
for i in $(seq 1 30); do [ -f mitm/mitmproxy-ca-cert.pem ] && break; sleep 1; done
# エージェントのコンテナが信頼する CA の束(システムの CA + mitmproxy の CA)
docker run --rm --entrypoint cat qwen-agent /etc/ssl/certs/ca-certificates.crt > ca/bundle.pem && cat mitm/mitmproxy-ca-cert.pem >> ca/bundle.pem && chmod 644 ca/bundle.pem
echo "proxy up (target=$P)"

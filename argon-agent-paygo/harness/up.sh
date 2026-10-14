#!/bin/bash
# 隔離環境を立ち上げる。agent はインターネットに出られない internal ネットワークだけにつなぐ
set -e
cd "$(dirname "$0")"
SA=argon-agent@${PROJECT_ID:?set PROJECT_ID}.iam.gserviceaccount.com
umask 077
gcloud auth print-access-token --impersonate-service-account=$SA 2>/dev/null > secrets/token
docker network inspect argon-int >/dev/null 2>&1 || docker network create --internal argon-int >/dev/null
docker rm -f argon-proxy >/dev/null 2>&1 || true
docker run -d --name argon-proxy --network bridge -e PROJECT=${PROJECT_ID:?set PROJECT_ID} -e ALLOW_MODELS="${ALLOW_MODELS-}" \
  -v "$PWD/secrets:/secrets:ro" -v "$PWD/logs:/logs" argon-proxy >/dev/null
docker network connect --alias proxy --alias collector argon-int argon-proxy
echo "proxy up (allow=${ALLOW_MODELS-})"

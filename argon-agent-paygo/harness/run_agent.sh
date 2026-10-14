#!/bin/bash
# usage: run_agent.sh WORKDIR OUT_PREFIX [gemini の引数...]
# 作業フォルダだけを /work にマウントし、internal ネットワークで gemini CLI を動かす
WORK="$1"; OUT="$2"; shift 2
docker run --rm --network argon-int \
  -e GOOGLE_GENAI_USE_VERTEXAI=true -e GOOGLE_CLOUD_PROJECT=${PROJECT_ID:?set PROJECT_ID} -e GOOGLE_CLOUD_LOCATION=global \
  -e GOOGLE_VERTEX_BASE_URL=http://proxy:8080 -e GCE_METADATA_HOST=proxy:8080 -e GCE_METADATA_IP=proxy:8080 \
  -v "$WORK:/work" ${SETTINGS:+-v "$SETTINGS:/home/agent/.gemini/settings.json:ro"} \
  argon-agent gemini "$@" > "$OUT.json" 2> "$OUT.err"
echo $?

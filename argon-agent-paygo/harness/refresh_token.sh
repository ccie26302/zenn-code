#!/bin/bash
# 30分ごとに、なりすましのトークンを更新する(1時間で切れるため)
cd "$(dirname "$0")"; umask 077
while true; do
  gcloud auth print-access-token --impersonate-service-account=argon-agent@${PROJECT_ID:?set PROJECT_ID}.iam.gserviceaccount.com 2>/dev/null > secrets/token.new && mv secrets/token.new secrets/token
  sleep 1800
done

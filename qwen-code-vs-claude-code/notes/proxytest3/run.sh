#!/bin/bash
# 読者向けの設定をホームに置いた Qwen Code を流し、試験用の中継が受けた外への接続を数える。usage: run.sh LABEL HOME_DIR [docker の追加引数...]
T=$(cd "$(dirname "$0")" && pwd); label=$1; home=$2; shift 2
n0=$(wc -l < $T/logs/gcp_requests.jsonl)
out=$(docker run --rm --network qwen-int-test --cap-drop ALL --security-opt no-new-privileges -e HTTPS_PROXY=http://proxy:3128 -e NO_PROXY=proxy -e SSL_CERT_FILE=/ca/bundle.pem -e NODE_EXTRA_CA_CERTS=/ca/bundle.pem -v "$T/ca:/ca:ro" -v "$home:/seed:ro" -v "$T/start.sh:/start.sh:ro" "$@" --entrypoint /start.sh qwen-agent 2>&1 | tail -1)
sleep 3
tail -n +$((n0+1)) $T/logs/gcp_requests.jsonl | python3 -c "
import sys,json,collections
c=collections.Counter(json.loads(l)['host'] for l in sys.stdin)
print(sys.argv[1], dict(c), 'answer=', repr(sys.argv[2][:10]))" "$label" "$out" | tee -a $T/result.txt

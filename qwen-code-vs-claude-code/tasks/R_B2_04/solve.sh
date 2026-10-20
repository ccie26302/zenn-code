#!/bin/bash
cd "$1"
git merge -q feature/retry >/dev/null 2>&1
printf 'DEFAULTS = {\n    "timeout": 60,\n    "endpoint": "https://api.example.com",\n    "region": "asia-northeast1",\n    "retries": 3,\n}\n' > config.py
cat > client.py <<'PY'
from config import DEFAULTS


def fetch(get, path):
    """get(url, timeout) を呼んで結果を返す。ConnectionError は retries 回まで試す"""
    url = DEFAULTS["endpoint"] + path + "?region=" + DEFAULTS["region"]
    last = None
    for _ in range(DEFAULTS["retries"]):
        try:
            return get(url, DEFAULTS["timeout"])
        except ConnectionError as e:
            last = e
    raise last
PY
git add -A && git commit -qm "Merge branch 'feature/retry'"

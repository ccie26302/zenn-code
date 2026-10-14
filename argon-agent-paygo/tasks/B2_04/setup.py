import os, subprocess, sys
sys.path.insert(0, "/tasks")
from jlib import write
ENV = dict(os.environ, GIT_AUTHOR_DATE="2026-01-01T00:00:00Z", GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
BASE = {
"config.py": 'DEFAULTS = {\n    "timeout": 30,\n    "endpoint": "https://api.example.com",\n}\n',
"client.py": 'from config import DEFAULTS\n\n\ndef fetch(get, path):\n    """get(url, timeout) を呼んで結果を返す"""\n    url = DEFAULTS["endpoint"] + path\n    return get(url, DEFAULTS["timeout"])\n',
"tests/test_base.py": 'from client import fetch\n\n\ndef test_fetch_returns():\n    assert fetch(lambda u, t: "ok", "/a") == "ok"\n',
}
MAIN = {
"config.py": 'DEFAULTS = {\n    "timeout": 60,\n    "endpoint": "https://api.example.com",\n    "region": "asia-northeast1",\n}\n',
"client.py": 'from config import DEFAULTS\n\n\ndef fetch(get, path):\n    """get(url, timeout) を呼んで結果を返す"""\n    url = DEFAULTS["endpoint"] + path + "?region=" + DEFAULTS["region"]\n    return get(url, DEFAULTS["timeout"])\n',
"tests/test_region.py": 'from client import fetch\n\n\ndef test_region_and_timeout():\n    seen = []\n    fetch(lambda u, t: seen.append((u, t)), "/a")\n    assert seen == [("https://api.example.com/a?region=asia-northeast1", 60)]\n',
}
FEAT = {
"config.py": 'DEFAULTS = {\n    "timeout": 30,\n    "endpoint": "https://api.example.com",\n    "retries": 3,\n}\n',
"client.py": 'from config import DEFAULTS\n\n\ndef fetch(get, path):\n    """get(url, timeout) を呼んで結果を返す。ConnectionError は retries 回まで試す"""\n    url = DEFAULTS["endpoint"] + path\n    last = None\n    for _ in range(DEFAULTS["retries"]):\n        try:\n            return get(url, DEFAULTS["timeout"])\n        except ConnectionError as e:\n            last = e\n    raise last\n',
"tests/test_retry.py": 'import pytest\nfrom client import fetch\n\n\ndef flaky(n):\n    calls = []\n    def get(u, t):\n        calls.append(u)\n        if len(calls) <= n:\n            raise ConnectionError("down")\n        return "ok"\n    return get, calls\n\n\ndef test_retry_then_ok():\n    get, calls = flaky(2)\n    assert fetch(get, "/a") == "ok" and len(calls) == 3\n\n\ndef test_retry_gives_up():\n    get, calls = flaky(5)\n    with pytest.raises(ConnectionError):\n        fetch(get, "/a")\n    assert len(calls) == 3\n',
}
if __name__ == "__main__":
    w = sys.argv[1]; g = lambda c: subprocess.run(c, cwd=w, shell=True, check=True, env=ENV, capture_output=True)
    g("git init -q -b main && git config user.name 'Dev' && git config user.email dev@example.com")
    write(w, BASE); g("git add -A && git commit -qm 'init'")
    g("git checkout -q -b feature/retry"); write(w, FEAT); g("git add -A && git commit -qm 'feat: retry on ConnectionError'")
    g("git checkout -q main"); write(w, MAIN); g("git add -A && git commit -qm 'feat: region and longer timeout'")

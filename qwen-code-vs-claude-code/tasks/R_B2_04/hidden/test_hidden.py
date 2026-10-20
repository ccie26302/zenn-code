import pytest
from client import fetch
from config import DEFAULTS
def test_both_settings():
    assert DEFAULTS["timeout"] == 60 and DEFAULTS["region"] == "asia-northeast1" and DEFAULTS["retries"] == 3
def test_retry_keeps_region_and_timeout():
    seen = []
    def get(u, t):
        seen.append((u, t))
        if len(seen) < 3: raise ConnectionError("x")
        return "ok"
    assert fetch(get, "/b") == "ok"
    assert seen == [("https://api.example.com/b?region=asia-northeast1", 60)] * 3

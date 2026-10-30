#!/usr/bin/env python3
"""伝播の確認: 各 SA で GET projects/P を叩き、期待どおり(ロールあり=200、none=403)が 10 回連続するまで待つ"""
import sys, time, json
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import P, PRINCIPALS, ROOT, call, token
log = open(ROOT / "data" / "probe.jsonl", "a")
for p in PRINCIPALS:
    want = 403 if p == "none" else 200
    streak, n, t0 = 0, 0, time.time()
    while streak < 10:
        st, _, date = call("GET", f"https://cloudresourcemanager.googleapis.com/v1/projects/{P}", token(p))
        n += 1
        streak = streak + 1 if st == want else 0
        log.write(json.dumps({"principal": p, "status": st, "date": date}) + "\n")
        time.sleep(1)
    print(f"{p}: ok after {n} calls, {time.time()-t0:.0f}s", flush=True)
print("PROBE_DONE", flush=True)

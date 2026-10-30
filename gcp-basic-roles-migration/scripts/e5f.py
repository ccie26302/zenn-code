#!/usr/bin/env python3
"""E5f: 外す前に権限を使っていたかで、取り消しの速さが変わるか(PLAN v2.10)"""
import json, random, sys, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import P, ROOT, call, classify
import iamedit
from e5 import M, op_c, tok
def op_k():
    st, body, d = call("GET", f"https://compute.googleapis.com/compute/v1/projects/{P}/zones/asia-northeast1-a/instances", tok(), timeout=20)
    return classify(st, body)
def both(want, cap=900):
    t0 = time.time(); tc = tk = None
    while time.time() - t0 < cap and (tc is None or tk is None):
        c = op_c()[0]; k = op_k(); now = round(time.time() - t0, 2)
        if tc is None and c == want: tc = now
        if tk is None and k == want: tk = now
        time.sleep(0.5)
    return tc, tk
out = open(ROOT / "data" / "e5f.jsonl", "a")
iamedit.modify(lambda bs: [b for b in bs if M not in b["members"]] + [dict(b, members=[m for m in b["members"] if m != M]) for b in bs if M in b["members"] and len(b["members"]) > 1])
trials = [c for c in ["idle", "busy"] for _ in range(10)]
random.Random(60).shuffle(trials)
for i, cond in enumerate(trials, 1):
    s = 0
    while s < 5:
        s = s + 1 if (op_c()[0] == "denied" and op_k() == "denied") else 0; time.sleep(0.5)
    t_add, _ = iamedit.add(M, "roles/editor")
    both("success")
    n_busy = 0
    while time.time() - t_add < 30:
        if cond == "busy":
            op_c(); n_busy += 1; time.sleep(0.5)
        else:
            time.sleep(0.2)
    t_rm, _ = iamedit.remove(M, "roles/editor")
    rc, rk = both("denied")
    rec = {"i": i, "cond": cond, "age_actual": round(t_rm - t_add, 2), "busy_calls": n_busy, "remove_pubsub": rc, "remove_compute": rk}
    out.write(json.dumps(rec) + "\n"); out.flush(); print(json.dumps(rec), flush=True)
iamedit.add(M, "roles/editor")
print("E5F_DONE", flush=True)

#!/usr/bin/env python3
"""E5c: 外したことが効くまでの時間を、Pub/Sub の発行と Compute のインスタンス一覧で同時に測る(Editor/Writer 各 10 回)"""
import json, sys, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import P, ROOT, call, classify
import iamedit, e5
from e5 import M, op_c, tok
def op_k():
    st, body, d = call("GET", f"https://compute.googleapis.com/compute/v1/projects/{P}/zones/asia-northeast1-a/instances", tok(), timeout=20)
    return classify(st, body)
out = open(ROOT / "data" / "e5c.jsonl", "a")
iamedit.modify(lambda bs: [b for b in bs if M not in b["members"]] + [dict(b, members=[m for m in b["members"] if m != M]) for b in bs if M in b["members"] and len(b["members"]) > 1])
def both(want, cap=1200):
    t0 = time.time(); tc = tk = None
    while time.time() - t0 < cap and (tc is None or tk is None):
        c = op_c()[0]; k = op_k(); now = round(time.time() - t0, 2)
        if tc is None and c == want: tc = now
        if tk is None and k == want: tk = now
        time.sleep(0.5)
    return tc, tk
for role in ["roles/editor", "roles/writer"]:
    for rep in range(1, 11):
        iamedit.add(M, role); gc, gk = both("success")
        s = 0
        while s < 5:
            s = s + 1 if (op_c()[0] == "success" and op_k() == "success") else 0; time.sleep(0.5)
        iamedit.remove(M, role); rc, rk = both("denied")
        rec = {"role": role, "rep": rep, "grant_pubsub": gc, "grant_compute": gk, "remove_pubsub": rc, "remove_compute": rk}
        out.write(json.dumps(rec) + "\n"); out.flush(); print(json.dumps(rec), flush=True)
        s = 0
        while s < 5:
            s = s + 1 if (op_c()[0] == "denied" and op_k() == "denied") else 0; time.sleep(0.5)
iamedit.add(M, "roles/editor")
print("E5C_DONE", flush=True)

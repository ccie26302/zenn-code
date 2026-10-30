#!/usr/bin/env python3
"""E5e: 付与の古さ(付けてから外すまでの時間)と、取り消しが効くまでの時間(PLAN v2.9)"""
import json, random, sys, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import P, ROOT, call, classify
import iamedit
from e5 import M, op_c, tok
def op_k():
    st, body, d = call("GET", f"https://compute.googleapis.com/compute/v1/projects/{P}/zones/asia-northeast1-a/instances", tok(), timeout=20)
    return classify(st, body)
def both(want, cap=1200):
    t0 = time.time(); tc = tk = None
    while time.time() - t0 < cap and (tc is None or tk is None):
        c = op_c()[0]; k = op_k(); now = round(time.time() - t0, 2)
        if tc is None and c == want: tc = now
        if tk is None and k == want: tk = now
        time.sleep(0.5)
    return tc, tk
out = open(ROOT / "data" / "e5e.jsonl", "a")
iamedit.modify(lambda bs: [b for b in bs if M not in b["members"]] + [dict(b, members=[m for m in b["members"] if m != M]) for b in bs if M in b["members"] and len(b["members"]) > 1])
trials = [a for a in [3, 30, 120] for _ in range(8)]
random.Random(59).shuffle(trials)
for i, age in enumerate(trials, 1):
    s = 0
    while s < 5:
        s = s + 1 if (op_c()[0] == "denied" and op_k() == "denied") else 0; time.sleep(0.5)
    t_add, _ = iamedit.add(M, "roles/editor")
    gc, gk = both("success")
    t_eff = time.time()
    while time.time() - t_add < age:
        time.sleep(0.2)
    t_rm, _ = iamedit.remove(M, "roles/editor")
    rc, rk = both("denied", cap=900)
    rec = {"i": i, "age_target": age, "age_actual": round(t_rm - t_add, 2), "grant_pubsub": gc, "grant_compute": gk,
           "remove_pubsub": rc, "remove_compute": rk}
    out.write(json.dumps(rec) + "\n"); out.flush(); print(json.dumps(rec), flush=True)
iamedit.add(M, "roles/editor")
print("E5E_DONE", flush=True)

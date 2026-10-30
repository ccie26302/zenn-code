#!/usr/bin/env python3
"""E5d: 置き換えの区間を、変更の前から連続して観察する(PLAN v2.8)"""
import json, random, sys, threading, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import ROOT
import iamedit, e5
from e5 import M, op_c
out = open(ROOT / "data" / "e5d.jsonl", "a"); summ = open(ROOT / "data" / "e5d_summary.jsonl", "a")
def reset_to_editor():
    iamedit.modify(lambda bs: [b for b in bs if M not in b["members"]] + [dict(b, members=[m for m in b["members"] if m != M]) for b in bs if M in b["members"] and len(b["members"]) > 1])
    iamedit.add(M, "roles/editor")
    s = 0
    while s < 10:
        s = s + 1 if op_c()[0] == "success" else 0; time.sleep(0.5)
trials = [m for m in ["remove_gap10_add", "add_then_remove", "atomic"] for _ in range(10)]
random.Random(58).shuffle(trials)
for i, method in enumerate(trials, 1):
    reset_to_editor()
    calls = []; stop = threading.Event()
    def probe():
        while not stop.is_set():
            t = time.time(); c, st, d = op_c(); calls.append((t, c, st, d)); time.sleep(0.5)
    th = threading.Thread(target=probe); th.start()
    time.sleep(5)
    t0 = time.time()
    if method == "remove_gap10_add":
        iamedit.remove(M, "roles/editor"); time.sleep(10); iamedit.add(M, "roles/writer")
    elif method == "add_then_remove":
        iamedit.add(M, "roles/writer"); iamedit.remove(M, "roles/editor")
    else:
        iamedit.replace(M, "roles/editor", "roles/writer")
    t1 = time.time()
    # 観察: 20 回連続の成功、または 120 秒
    while time.time() - t1 < 120:
        tail = [c for (_, c, _, _) in calls[-20:]]
        if len(tail) == 20 and all(c == "success" for c in tail) and calls[-20][0] > t1:
            break
        time.sleep(1)
    stop.set(); th.join()
    for (t, c, st, d) in calls:
        out.write(json.dumps({"i": i, "method": method, "dt": round(t - t0, 3), "class": c, "status": st, "date": d}) + "\n")
    after = [(t - t0, c) for (t, c, _, _) in calls if t >= t0]
    den = [x for x, c in after if c == "denied"]
    rec = {"i": i, "method": method, "change_sec": round(t1 - t0, 2), "calls_after": len(after), "denied_n": len(den),
           "first_denied": round(den[0], 2) if den else None, "last_denied": round(den[-1], 2) if den else None,
           "net_err": sum(1 for _, c in after if c == "undetermined")}
    summ.write(json.dumps(rec) + "\n"); summ.flush(); out.flush(); print(json.dumps(rec), flush=True)
reset_to_editor()
print("E5D_DONE", flush=True)

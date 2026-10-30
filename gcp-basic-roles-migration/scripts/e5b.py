#!/usr/bin/env python3
"""E5b: 外したことが効くまでの時間と、付けたことが効くまでの時間(Editor と Writer、各 10 回)"""
import json, sys, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import ROOT
import iamedit, e5
from e5 import M, op_c
out = open(ROOT / "data" / "e5b.jsonl", "a")
def until(want, cap=900):
    t0 = time.time(); calls = 0; s = 0
    while time.time() - t0 < cap:
        c, st, d = op_c(); calls += 1
        if c == want:
            return round(time.time() - t0, 2), calls
        time.sleep(0.5)
    return None, calls
# 初期化: e5swap の付与をいったん全部外す
iamedit.modify(lambda bs: [b for b in bs if M not in b["members"]] + [dict(b, members=[m for m in b["members"] if m != M]) for b in bs if M in b["members"] and len(b["members"]) > 1])
for role in ["roles/editor", "roles/writer"]:
    for rep in range(1, 11):
        # 付けたことが効くまで
        t_add, _ = iamedit.add(M, role); g, n1 = until("success")
        # 安定を待つ(5 回連続で成功)
        e5.wait_state("success", "denied" if role == "roles/editor" else "success", n=5)
        t_rm, _ = iamedit.remove(M, role); r, n2 = until("denied")
        rec = {"role": role, "rep": rep, "grant_effective_s": g, "remove_effective_s": r}
        out.write(json.dumps(rec) + "\n"); out.flush(); print(json.dumps(rec), flush=True)
        # 次の回の前に、5 回連続で拒否を確かめる
        s = 0
        while s < 5:
            c, _, _ = op_c(); s = s + 1 if c == "denied" else 0; time.sleep(0.5)
iamedit.add(M, "roles/editor")
print("E5B_DONE", flush=True)

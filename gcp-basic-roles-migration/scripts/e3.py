#!/usr/bin/env python3
"""E3: 各主体 × 各操作 × 3回。testIamPermissions の予測と、実際の結果を記録する。
使い方: scripts/e3.py [--reps 3] [--seed 20261030] [--only op1,op2] [--principals a,b] [--label main]
出力: data/e3_<label>.jsonl(1行1試行)"""
import argparse, json, random, sys, time, uuid, urllib.parse
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import P, PRINCIPALS, ROOT, call, classify, short, token, user_token
from e3_ops import OPS, S, BQ, PS, SM, IAM, CRM, QP

def test_perms(spec, tok):
    """戻り値: (予測 True/False/None, 詳細)"""
    kind = spec[0]
    if kind == "multi":
        res = [test_perms(s, tok) for s in spec[1]]
        if any(r[0] is None for r in res):
            return None, [r[1] for r in res]
        return all(r[0] for r in res), [r[1] for r in res]
    if kind == "project":
        perms = spec[1]
        st, body, _ = call("POST", f"{CRM}:testIamPermissions", tok, {"permissions": perms})
    elif kind == "bucket":
        perms = spec[2]
        q = "&".join("permissions=" + urllib.parse.quote(p) for p in perms)
        st, body, _ = call("GET", f"{S}/b/{spec[1]}/iam/testPermissions?{q}", tok)
    elif kind == "bqtable":
        perms = spec[3]
        st, body, _ = call("POST", f"{BQ}/datasets/{spec[1]}/tables/{spec[2]}:testIamPermissions", tok, {"permissions": perms})
    elif kind == "topic":
        perms = spec[2]
        st, body, _ = call("POST", f"{PS}/topics/{spec[1]}:testIamPermissions", tok, {"permissions": perms})
    elif kind == "secret":
        perms = spec[2]
        st, body, _ = call("POST", f"{SM}/secrets/{spec[1]}:testIamPermissions", tok, {"permissions": perms})
    elif kind == "sa":
        perms = spec[2]
        st, body, _ = call("POST", f"{IAM}/projects/-/serviceAccounts/{spec[1]}:testIamPermissions", tok, {"permissions": perms})
    else:
        return None, "unknown"
    if st != 200:
        return None, f"{st} {short(body, 150)}"
    j = json.loads(body or "{}")
    granted = set(j.get("permissions", []) or [])
    return all(p in granted for p in perms), sorted(granted)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20261030)
    ap.add_argument("--only", default="")
    ap.add_argument("--principals", default=",".join(PRINCIPALS + ["me"]))
    ap.add_argument("--label", default="main")
    a = ap.parse_args()
    ops = [o for o in OPS if not a.only or o["name"] in a.only.split(",")]
    principals = a.principals.split(",")
    trials = [(p, o["name"], r) for p in principals for o in ops for r in range(1, a.reps + 1)]
    random.Random(a.seed).shuffle(trials)
    byname = {o["name"]: o for o in ops}
    out = open(ROOT / "data" / f"e3_{a.label}.jsonl", "a")
    print(f"{len(trials)} trials", flush=True)
    for i, (p, name, rep) in enumerate(trials, 1):
        o = byname[name]
        u = uuid.uuid4().hex[:10]
        tok = token(p)
        hdr = QP if p == "me" else None
        if o["setup"]:
            o["setup"](u)
        pred, pdet = test_perms(o["test"], tok)
        t0 = time.time()
        try:
            st, body, verified = o["run"](tok, u)
        except Exception as e:
            st, body, verified = -1, repr(e), None
        dt = time.time() - t0
        cls = classify(st, body)
        if cls == "success" and verified is False:
            cls = "success_unverified"
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "principal": p, "op": name, "group": o["group"],
               "rep": rep, "uniq": u, "status": st, "class": cls, "verified": verified, "pred": pred,
               "pred_detail": pdet, "detail": short(body), "sec": round(dt, 2)}
        out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush()
        if o["cleanup"]:
            try:
                o["cleanup"](u)
            except Exception as e:
                print("cleanup error", name, u, e, flush=True)
        if i % 25 == 0:
            print(f"{i}/{len(trials)}", flush=True)
    print("E3_DONE", flush=True)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""E5: Editor → Writer の置き換えを 3 方式で行い、代表の操作が止まった時間を測る。
方式: remove_first(外してから付ける)/ add_first(付けてから外す)/ atomic(1回の setIamPolicy)
代表の操作: op_c = Pub/Sub への発行(Editor も Writer も持つ)、op_r = 締め出したバケット(rfg)の読み取り(Editor は拒否、Writer は通るはず)
出力: data/e5_<label>.jsonl(1行1回の呼び出し)、data/e5_<label>_summary.jsonl(1行1試行)"""
import argparse, base64, json, random, sys, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import P, ROOT, call, token, classify
import iamedit

SA = f"br-e5swap@{P}.iam.gserviceaccount.com"
M = f"serviceAccount:{SA}"
PS = f"https://pubsub.googleapis.com/v1/projects/{P}/topics/br-topic:publish"
RFG = f"https://storage.googleapis.com/storage/v1/b/{P}-rfg/o/seed.txt?alt=media"

_tok = {"t": None, "at": 0}
def tok():
    # SA のトークンは IAM の付与と無関係に取れる(自分に tokenCreator がある)。50 分ごとに取り直す
    if time.time() - _tok["at"] > 3000:
        import brlib
        brlib._sa_tok.pop("e5", None)
        st, body, _ = call("POST", f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{SA}:generateAccessToken",
                           brlib.user_token(), {"scope": ["https://www.googleapis.com/auth/cloud-platform"], "lifetime": "3600s"})
        _tok["t"] = json.loads(body)["accessToken"]; _tok["at"] = time.time()
    return _tok["t"]

def op_c():
    st, body, date = call("POST", PS, tok(), {"messages": [{"data": base64.b64encode(b"e5").decode()}]}, timeout=20)
    return classify(st, body), st, date

def op_r():
    st, body, date = call("GET", RFG, tok(), timeout=20)
    return classify(st, body), st, date

def wait_state(want_c, want_r, n=5, cap=1200, log=None, tag=""):
    """op_c と op_r が、それぞれ want の結果を n 回連続で返すまで待つ"""
    sc = sr = 0; t0 = time.time()
    while sc < n or sr < n:
        c, st1, d1 = op_c(); r, st2, d2 = op_r()
        sc = sc + 1 if c == want_c else 0
        sr = sr + 1 if r == want_r else 0
        if log:
            log.write(json.dumps({"tag": tag, "t": time.time(), "c": c, "cs": st1, "r": r, "rs": st2, "date": d1}) + "\n")
        if time.time() - t0 > cap:
            return False, time.time() - t0
        time.sleep(0.5)
    return True, time.time() - t0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--label", default="main")
    ap.add_argument("--observe", type=int, default=600, help="変更後に観察する秒数の上限")
    a = ap.parse_args()
    log = open(ROOT / "data" / f"e5_{a.label}.jsonl", "a")
    summ = open(ROOT / "data" / f"e5_{a.label}_summary.jsonl", "a")
    trials = [m for m in ["remove_first", "add_first", "atomic"] for _ in range(a.n)]
    random.Random(a.seed).shuffle(trials)
    # 初期状態: Editor だけ
    pol = iamedit.get()
    has_editor = any(b["role"] == "roles/editor" and M in b["members"] for b in pol["bindings"])
    if not has_editor:
        iamedit.add(M, "roles/editor")
    for i, method in enumerate(trials, 1):
        ok, waited = wait_state("success", "denied", log=log, tag=f"{i}-pre")
        if not ok:
            print("pre-state not reached", i, flush=True); continue
        # 置き換え
        if method == "remove_first":
            t_change, _ = iamedit.remove(M, "roles/editor")
            t2, _ = iamedit.add(M, "roles/writer")
        elif method == "add_first":
            t_change, _ = iamedit.add(M, "roles/writer")
            t2, _ = iamedit.remove(M, "roles/editor")
        else:
            t_change, _ = iamedit.replace(M, "roles/editor", "roles/writer")
            t2 = t_change
        # 観察: op_c が成功 20 回連続、op_r が成功 20 回連続になるまで
        calls = []; sc = sr = 0; t0 = time.time()
        while (sc < 20 or sr < 20) and time.time() - t0 < a.observe:
            c, st1, d1 = op_c(); r, st2, d2 = op_r(); now = time.time()
            calls.append((now - t_change, c, r))
            log.write(json.dumps({"tag": f"{i}-obs", "method": method, "dt": round(now - t_change, 3), "c": c, "cs": st1,
                                  "r": r, "rs": st2, "date": d1}) + "\n")
            sc = sc + 1 if c == "success" else 0
            sr = sr + 1 if r == "success" else 0
            time.sleep(0.5)
        c_denied = [x[0] for x in calls if x[1] != "success"]
        r_ok = [x[0] for x in calls if x[2] == "success"]
        rec = {"i": i, "method": method, "t_change": t_change, "t_second_call": t2,
               "n_calls": len(calls), "c_denied_n": len(c_denied),
               "c_first_denied": round(c_denied[0], 2) if c_denied else None,
               "c_last_denied": round(c_denied[-1], 2) if c_denied else None,
               "r_first_ok": round(r_ok[0], 2) if r_ok else None,
               "settled": sc >= 20 and sr >= 20, "observed_sec": round(time.time() - t0, 1)}
        summ.write(json.dumps(rec) + "\n"); summ.flush(); log.flush()
        print(json.dumps(rec), flush=True)
        # 元に戻す: Writer を外して Editor を付ける(先に足す)
        iamedit.add(M, "roles/editor"); iamedit.remove(M, "roles/writer")
    print("E5_DONE", flush=True)

if __name__ == "__main__":
    main()

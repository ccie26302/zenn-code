#!/usr/bin/env python3
"""E4: 条件付きの Writer の効き方。
(i) expiry: 期限付きの Writer。期限の前後 2 分を 2 秒おきに試す。5 回
(ii) names: resource.name で対象を絞った Writer。対応するサービスと、しないサービスの両側。2 通りの書き方 × 3 回
出力: data/e4_<label>.jsonl"""
import argparse, base64, json, sys, time, datetime
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import P, PN, ROOT, call, classify, short, user_token
import iamedit

SA = f"br-e4cond@{P}.iam.gserviceaccount.com"
M = f"serviceAccount:{SA}"
_tok = {"t": None, "at": 0}
def tok():
    if time.time() - _tok["at"] > 3000:
        st, body, _ = call("POST", f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{SA}:generateAccessToken",
                           user_token(), {"scope": ["https://www.googleapis.com/auth/cloud-platform"], "lifetime": "3600s"})
        _tok["t"] = json.loads(body)["accessToken"]; _tok["at"] = time.time()
    return _tok["t"]

def publish():
    st, body, d = call("POST", f"https://pubsub.googleapis.com/v1/projects/{P}/topics/br-topic:publish", tok(),
                       {"messages": [{"data": base64.b64encode(b"e4").decode()}]}, timeout=20)
    return classify(st, body), st, body, d

def remove_all():
    iamedit.modify(lambda bs: [b for b in bs if M not in b["members"]] +
                   [dict(b, members=[m for m in b["members"] if m != M]) for b in bs if M in b["members"] and len(b["members"]) > 1])

def wait_for(fn, want, n=5, cap=1200):
    s = 0; t0 = time.time()
    while s < n:
        r = fn()[0]
        s = s + 1 if r == want else 0
        if time.time() - t0 > cap:
            return False
        time.sleep(1)
    return True

def expiry(out, reps):
    for rep in range(1, reps + 1):
        remove_all(); wait_for(publish, "denied")
        T = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0) + datetime.timedelta(minutes=7)
        Ts = T.strftime("%Y-%m-%dT%H:%M:%SZ")
        iamedit.add(M, "roles/writer", {"title": "e4-expiry", "expression": f"request.time < timestamp('{Ts}')"})
        if not wait_for(publish, "success", cap=400):
            out.write(json.dumps({"exp": "expiry", "rep": rep, "error": "never became effective", "T": Ts}) + "\n"); continue
        Tt = T.timestamp()
        while time.time() < Tt - 120:
            time.sleep(1)
        while time.time() < Tt + 120:
            c, st, body, d = publish()
            out.write(json.dumps({"exp": "expiry", "rep": rep, "T": Ts, "dt_local": round(time.time() - Tt, 3),
                                  "server_date": d, "class": c, "status": st}) + "\n")
            time.sleep(2)
        out.flush()
        # 期限切れのバインディングがポリシーに残っているか
        pol = iamedit.get()
        left = [b for b in pol["bindings"] if M in b["members"]]
        out.write(json.dumps({"exp": "expiry_left", "rep": rep, "bindings_left": left}) + "\n"); out.flush()
        print("expiry rep", rep, "done", flush=True)
    remove_all()

def names_tests():
    S = "https://storage.googleapis.com/storage/v1"
    BQ = f"https://bigquery.googleapis.com/bigquery/v2/projects/{P}"
    SM = f"https://secretmanager.googleapis.com/v1/projects/{P}"
    t = tok()
    def g(url):
        st, body, _ = call("GET", url, t, timeout=30); return st, body
    def p(url, b):
        st, body, _ = call("POST", url, t, b, timeout=30); return st, body
    return {
        "gcs_match_read":      lambda: g(f"{S}/b/{P}-ubla/o/seed.txt?alt=media"),
        "gcs_nomatch_read":    lambda: g(f"{S}/b/{P}-rubla/o/seed.txt?alt=media"),
        "gcs_match_list":      lambda: g(f"{S}/b/{P}-ubla/o"),
        "secret_match":        lambda: g(f"{SM}/secrets/br-secret/versions/latest:access"),
        "secret_nomatch":      lambda: g(f"{SM}/secrets/br-secret2/versions/latest:access"),
        "bq_match_read":       lambda: g(f"{BQ}/datasets/br_restr/tables/t1/data?maxResults=1"),
        "bq_nomatch_read":     lambda: g(f"{BQ}/datasets/br_default/tables/t1/data?maxResults=1"),
        "pubsub_match_pub":    lambda: p(f"https://pubsub.googleapis.com/v1/projects/{P}/topics/br-topic:publish", {"messages": [{"data": "ZTQ="}]}),
        "pubsub_nomatch_pub":  lambda: p(f"https://pubsub.googleapis.com/v1/projects/{P}/topics/br-topic2:publish", {"messages": [{"data": "ZTQ="}]}),
        "compute_list":        lambda: g(f"https://compute.googleapis.com/compute/v1/projects/{P}/zones/asia-northeast1-a/instances"),
        "bucket_list":         lambda: g(f"{S}/b?project={P}"),
    }

def names(out, reps):
    strict = " || ".join([
        f"resource.name.startsWith('projects/_/buckets/{P}-ubla')",
        f"resource.name.startsWith('projects/{PN}/secrets/br-secret/')",
        f"resource.name == 'projects/{PN}/secrets/br-secret'",
        f"resource.name.startsWith('projects/{P}/datasets/br_restr')",
        f"resource.name == 'projects/{P}/topics/br-topic'",
    ])
    escape = "(" + strict + ") || !(resource.service in ['storage.googleapis.com', 'secretmanager.googleapis.com', 'bigquery.googleapis.com'])"
    for variant, expr in [("strict", strict), ("escape", escape), ("unconditional", None)]:
        remove_all()
        wait_for(lambda: (classify(*names_tests()["gcs_match_read"]()),), "denied")
        cond = {"title": f"e4-{variant}", "expression": expr} if expr else None
        iamedit.add(M, "roles/writer", cond)
        ok = wait_for(lambda: (classify(*names_tests()["gcs_match_read"]()),), "success", cap=600)
        time.sleep(120)  # 条件付きの評価が他のサービスにも行き渡るよう、さらに 2 分待つ
        for rep in range(1, reps + 1):
            for name, fn in names_tests().items():
                st, body = fn()
                out.write(json.dumps({"exp": "names", "variant": variant, "rep": rep, "test": name, "status": st,
                                      "class": classify(st, body), "detail": short(body, 200), "effective": ok}) + "\n")
            out.flush(); time.sleep(20)
        print("names", variant, "done", flush=True)
    remove_all()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="names,expiry")
    ap.add_argument("--label", default="main")
    ap.add_argument("--expiry-reps", type=int, default=5)
    a = ap.parse_args()
    out = open(ROOT / "data" / f"e4_{a.label}.jsonl", "a")
    if "names" in a.part:
        names(out, 3)
    if "expiry" in a.part:
        expiry(out, a.expiry_reps)
    print("E4_DONE", flush=True)

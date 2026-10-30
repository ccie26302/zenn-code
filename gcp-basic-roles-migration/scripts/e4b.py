#!/usr/bin/env python3
"""E4 の補い(PLAN v2.2 と v2.5): 逃がし方の書き方の違いと、secrets.get での条件の効き方"""
import json, sys, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import P, PN, ROOT, call, classify, short
import iamedit, e4
from e4 import M, remove_all, wait_for, names_tests

strict = " || ".join([
    f"resource.name.startsWith('projects/_/buckets/{P}-ubla')",
    f"resource.name.startsWith('projects/{PN}/secrets/br-secret/')",
    f"resource.name == 'projects/{PN}/secrets/br-secret'",
    f"resource.name.startsWith('projects/{P}/datasets/br_restr')",
    f"resource.name == 'projects/{P}/topics/br-topic'",
])
SVC = ["storage.googleapis.com", "secretmanager.googleapis.com", "bigquery.googleapis.com"]
TYPES = ["storage.googleapis.com/Object", "storage.googleapis.com/Bucket", "bigquery.googleapis.com/Table",
         "bigquery.googleapis.com/Dataset", "secretmanager.googleapis.com/Secret", "secretmanager.googleapis.com/SecretVersion"]
VARIANTS = [
    ("strict_ne_service", f"({strict}) || (" + " && ".join(f"resource.service != '{s}'" for s in SVC) + ")"),
    ("strict_ne_type", f"({strict}) || (" + " && ".join(f"resource.type != '{t}'" for t in TYPES) + ")"),
    ("escape_only_in", "!(resource.service in [" + ", ".join(f"'{s}'" for s in SVC) + "])"),
    ("strict_again", strict),
]
def tests():
    t = names_tests()
    SM = f"https://secretmanager.googleapis.com/v1/projects/{P}"
    tok = e4.tok()
    t["secret_get_match"] = lambda: call("GET", f"{SM}/secrets/br-secret", tok)[:2]
    t["secret_get_nomatch"] = lambda: call("GET", f"{SM}/secrets/br-secret2", tok)[:2]
    return t
out = open(ROOT / "data" / "e4b.jsonl", "a")
for variant, expr in VARIANTS:
    remove_all()
    wait_for(lambda: (classify(*names_tests()["gcs_match_read"]()),), "denied")
    iamedit.add(M, "roles/writer", {"title": f"e4b-{variant}", "expression": expr})
    ok = wait_for(lambda: (classify(*names_tests()["gcs_match_read"]()),), "success", cap=600)
    time.sleep(120)
    for rep in range(1, 4):
        for name, fn in tests().items():
            st, body = fn()
            out.write(json.dumps({"variant": variant, "rep": rep, "test": name, "status": st, "class": classify(st, body),
                                  "detail": short(body, 200), "effective": ok, "expr": expr if rep == 1 and name == "gcs_match_read" else None}) + "\n")
        out.flush(); time.sleep(20)
    print(variant, "done", flush=True)
remove_all()
print("E4B_DONE", flush=True)

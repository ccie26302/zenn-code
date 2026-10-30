#!/usr/bin/env python3
"""E1: 旧ロールと新ロールの権限の差分。E0 で最も多く出た集合を使う。
出力: data/e1_diff.csv(片方だけにある権限)、data/e1_dangerous.csv(危険な権限の表)、標準出力に要約"""
import csv, collections, pathlib, sys

base = pathlib.Path(__file__).resolve().parent.parent / "data"
label = sys.argv[1] if len(sys.argv) > 1 else "day1"
rows = list(csv.DictReader(open(base / f"e0_{label}.csv")))
mode = {}
for role in ["owner", "admin", "editor", "writer", "viewer", "reader"]:
    c = collections.Counter(r["sha256"] for r in rows if r["role"] == role)
    mode[role] = c.most_common(1)[0][0]
perms = {r: set(open(base / "e0_sets" / f"{r}_{h}.txt").read().split()) for r, h in mode.items()}

pairs = [("owner", "admin"), ("editor", "writer"), ("viewer", "reader")]
with open(base / "e1_diff.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["pair", "side", "service", "permission"])
    for old, new in pairs:
        for side, s in [(f"{old}_only", perms[old] - perms[new]), (f"{new}_only", perms[new] - perms[old])]:
            for p in sorted(s):
                w.writerow([f"{old}-{new}", side, p.split(".")[0], p])
            svc = collections.Counter(p.split(".")[0] for p in s)
            print(f"{old}->{new} {side}: {len(s)}  " + ", ".join(f"{k} {v}" for k, v in svc.most_common(8)))
    print()

danger = """resourcemanager.projects.setIamPolicy iam.serviceAccounts.setIamPolicy storage.buckets.setIamPolicy
bigquery.datasets.setIamPolicy iam.roles.create iam.roles.update iam.denypolicies.create
iam.serviceAccounts.actAs iam.serviceAccounts.getAccessToken iam.serviceAccounts.signBlob
iam.serviceAccounts.signJwt iam.serviceAccounts.implicitDelegation iam.serviceAccountKeys.create
storage.hmacKeys.create apikeys.keys.create secretmanager.versions.access billing.resourceAssociations.create
resourcemanager.projects.createBillingAssignment logging.sinks.delete logging.buckets.update logging.buckets.delete""".split()
order = ["owner", "admin", "editor", "writer", "viewer", "reader"]
with open(base / "e1_dangerous.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["permission"] + order)
    print(f"{'permission':45s} " + " ".join(f"{r:6s}" for r in order))
    for p in danger:
        flags = ["1" if p in perms[r] else "0" for r in order]
        w.writerow([p] + flags)
        print(f"{p:45s} " + " ".join(f"{('o' if x == '1' else '-'):6s}" for x in flags))
print("\nsizes:", {r: len(perms[r]) for r in order})

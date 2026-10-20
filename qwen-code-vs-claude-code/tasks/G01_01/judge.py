import csv, os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
w = sys.argv[1]; p = os.path.join(w, "inventory.csv")
exp = {("bucket", b) for b in G.buckets()} | {("service_account", s) for s in G.sas()} | {("cloud_run_service", s) for s in G.run_list()}
if ck("inventory.csv がある", os.path.exists(p)):
    rows = list(csv.reader(open(p, encoding="utf-8-sig")))
    ck("見出しが kind,name", rows and [c.strip() for c in rows[0]] == ["kind", "name"], rows[:1])
    got = {(r[0].strip(), r[1].strip()) for r in rows[1:] if len(r) >= 2}
    ck("実際の一覧と一致", got == exp, "多い %s / 足りない %s" % (sorted(got - exp)[:3], sorted(exp - got)[:3]))
done()

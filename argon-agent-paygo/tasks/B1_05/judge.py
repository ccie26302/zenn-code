import csv, os, re, sys
from collections import Counter
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done
from setup import gen
w = sys.argv[1]
OK = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z (INFO|DEBUG|WARN|ERROR) \[([^\]\s]+)\] (.*)$")
cnt, bad = Counter(), 0
for txt in gen().values():
    for ln in txt.split("\n")[:-1]:
        m = OK.match(ln)
        if not m: bad += 1; continue
        if m.group(1) == "ERROR":
            c = re.search(r"\bE\d{3}\b", m.group(3)); cnt[(m.group(2), c.group(0) if c else "NONE")] += 1
exp = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))
p = os.path.join(w, "error_summary.csv")
if ck("error_summary.csv がある", os.path.exists(p)):
    rows = list(csv.reader(open(p, newline="", encoding="utf-8-sig")))
    ck("ヘッダー", rows and [c.strip() for c in rows[0]] == ["component", "code", "count"], rows[:1])
    got = [((r[0].strip(), r[1].strip()), int(r[2])) for r in rows[1:] if r]
    ck("件数が正しい", dict(got) == dict(exp), [g for g in got if g not in exp][:4])
    ck("並び順", got == exp)
q = os.path.join(w, "malformed.txt")
if ck("malformed.txt がある", os.path.exists(q)):
    v = open(q).read().strip()
    ck("壊れた行の数(%d)" % bad, v == str(bad), v[:40])
done()

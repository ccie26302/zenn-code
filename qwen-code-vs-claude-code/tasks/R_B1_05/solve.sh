#!/bin/bash
cd "$1"
python3 - <<'PY'
import csv, glob, gzip, re
from collections import Counter
OK = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z (INFO|DEBUG|WARN|ERROR) \[([^\]\s]+)\] (.*)$")
cnt, bad = Counter(), 0
for p in sorted(glob.glob("logs/*")):
    f = gzip.open(p, "rt") if p.endswith(".gz") else open(p)
    for ln in f.read().split("\n")[:-1]:
        m = OK.match(ln)
        if not m: bad += 1; continue
        if m.group(1) == "ERROR":
            c = re.search(r"\bE\d{3}\b", m.group(3)); cnt[(m.group(2), c.group(0) if c else "NONE")] += 1
w = csv.writer(open("error_summary.csv", "w", newline="")); w.writerow(["component", "code", "count"])
for (c, k), n in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1])): w.writerow([c, k, n])
open("malformed.txt", "w").write("%d\n" % bad)
PY

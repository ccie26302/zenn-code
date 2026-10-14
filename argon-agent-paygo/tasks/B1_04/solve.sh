#!/bin/bash
cd "$1"
python3 - <<'PY'
import csv, datetime, os
rows = []
for d, _, fs in os.walk("project"):
    for f in fs:
        p = os.path.join(d, f); st = os.stat(p)
        if f.endswith(".log") and st.st_size >= 102400:
            rows.append((os.path.relpath(p, "project"), st.st_size, datetime.datetime.fromtimestamp(int(st.st_mtime), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
w = csv.writer(open("report.csv", "w", newline="")); w.writerow(["path", "size_bytes", "mtime"]); w.writerows(sorted(rows))
PY

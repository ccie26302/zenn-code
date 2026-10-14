#!/bin/bash
cd "$1"; mkdir -p out
python3 - <<'PY'
import csv, glob, os, sqlite3
con = sqlite3.connect("out/data.db")
for p in sorted(glob.glob("data/*.csv")):
    t = os.path.splitext(os.path.basename(p))[0]
    head, *rows = list(csv.reader(open(p, encoding="utf-8", newline="")))
    isint = [all(r[i].lstrip("-").isdigit() for r in rows) for i in range(len(head))]
    con.execute("CREATE TABLE %s (%s)" % (t, ", ".join('"%s" %s' % (h, "INTEGER" if k else "TEXT") for h, k in zip(head, isint))))
    con.executemany("INSERT INTO %s VALUES (%s)" % (t, ",".join("?" * len(head))), [[int(v) if k else v for v, k in zip(r, isint)] for r in rows])
con.commit()
PY

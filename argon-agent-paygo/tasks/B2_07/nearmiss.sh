#!/bin/bash
# 惜しい誤答: sqlite3 の .import と同じく、全部の列を TEXT で入れる(整数の列が文字列になる)
cd "$1"; mkdir -p out
python3 - <<'PY'
import csv, glob, os, sqlite3
con = sqlite3.connect("out/data.db")
for p in sorted(glob.glob("data/*.csv")):
    t = os.path.splitext(os.path.basename(p))[0]
    head, *rows = list(csv.reader(open(p, encoding="utf-8", newline="")))
    isint = [all(r[i].lstrip("-").isdigit() for r in rows) for i in range(len(head))]
    con.execute("CREATE TABLE %s (%s)" % (t, ", ".join('"%s" %s' % (h, "TEXT") for h, k in zip(head, isint))))
    con.executemany("INSERT INTO %s VALUES (%s)" % (t, ",".join("?" * len(head))), [[v for v in r] for r in rows])
con.commit()
PY

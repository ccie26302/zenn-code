#!/bin/bash
# 惜しい誤答: 連番を000から始める
cd "$1/photos"
python3 - <<'PY'
import os, re
rows = []
for n in os.listdir("."):
    m = re.search(r"(\d{4})[-_]?(\d{1,2})[-_]?(\d{1,2})", n)
    if re.search(r"\d{8}", n):
        s = re.search(r"(\d{4})(\d{2})(\d{2})", n); y, mo, d = map(int, s.groups())
    else:
        y, mo, d = map(int, m.groups())
    rows.append(((y, mo, d), n))
rows.sort()
tmp = []
for i, ((y, mo, d), n) in enumerate(rows):
    t = ".tmp%03d" % i; os.rename(n, t); tmp.append((t, "%03d_%04d-%02d-%02d.jpg" % (i, y, mo, d)))
for t, n in tmp: os.rename(t, n)
PY

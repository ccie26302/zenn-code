#!/bin/bash
# 惜しい誤答: 拡張子の大文字(JPG, PDF)を種類に当てはめられず、inbox に残す
cd "$1"
python3 - <<'PY'
import os, re, shutil
K = {"jpg": "images", "png": "images", "pdf": "docs", "docx": "docs", "txt": "docs", "xlsx": "sheets", "csv": "sheets"}
for n in sorted(os.listdir("inbox")):
    e = n.rsplit(".", 1)[1]
    if e not in K: continue
    m = re.search(r"(?<!\d)(\d{8})(?!\d)", n)
    ym = m.group(1)[:4] + "-" + m.group(1)[4:6] if m else "unknown"
    os.makedirs("sorted/%s/%s" % (K[e], ym), exist_ok=True)
    shutil.move("inbox/" + n, "sorted/%s/%s/%s" % (K[e], ym, n))
PY

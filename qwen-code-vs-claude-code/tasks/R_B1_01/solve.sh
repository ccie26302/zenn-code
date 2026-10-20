#!/bin/bash
cd "$1"
python3 - <<'PY'
import os, re, shutil
K = {"jpg": "images", "png": "images", "pdf": "docs", "docx": "docs", "txt": "docs", "xlsx": "sheets", "csv": "sheets"}
for n in sorted(os.listdir("inbox")):
    k = K[n.rsplit(".", 1)[1].lower()]
    m = re.search(r"(?<!\d)(\d{8})(?!\d)", n)
    ym = m.group(1)[:4] + "-" + m.group(1)[4:6] if m else "unknown"
    os.makedirs("sorted/%s/%s" % (k, ym), exist_ok=True)
    shutil.move("inbox/" + n, "sorted/%s/%s/%s" % (k, ym, n))
PY

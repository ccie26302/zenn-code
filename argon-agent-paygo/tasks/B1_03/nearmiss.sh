#!/bin/bash
# 惜しい誤答: 移動せずに削除する
cd "$1"
python3 - <<'PY'
import hashlib, os, shutil
from collections import defaultdict
g = defaultdict(list)
for d, _, fs in os.walk("docs"):
    for f in fs:
        p = os.path.join(d, f); g[hashlib.sha256(open(p, "rb").read()).hexdigest()].append(os.path.relpath(p, "docs"))
for rels in g.values():
    for r in sorted(rels)[1:]:
        os.makedirs(os.path.dirname(os.path.join("duplicates", r)) or "duplicates", exist_ok=True)
        os.remove(os.path.join("docs", r))
PY

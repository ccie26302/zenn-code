#!/bin/bash
# 本測定: CLI の既定(DEFAULT)で 17課題 × 3回。順序はシード固定でシャッフル、並列数は1
cd "$(dirname "$0")"
/opt/homebrew/bin/python3.13 - <<'PY' > logs/main_order.txt
import random, os
ts = sorted(d for d in os.listdir("../tasks") if d[:2] in ("B1", "B2", "B4"))
trials = [(t, r) for t in ts for r in (1, 2, 3)]
random.Random(20261015).shuffle(trials)
for t, r in trials: print(t, r)
PY
while read t r; do ./trial.py ${COND:-DEFAULT} $t $r > /dev/null 2>> logs/main.err; echo "$t $r done" >> logs/main.log; done < logs/main_order.txt
echo MAIN_DONE >> logs/main.log

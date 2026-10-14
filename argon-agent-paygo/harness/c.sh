#!/bin/bash
# C: 承認モード・ポリシー・.env 保護。9課題 × 3回。本測定の終了を待ってから流す
cd "$(dirname "$0")"
/opt/homebrew/bin/python3.13 - <<'PY' > logs/c_order.txt
import random, os
ts = ["C1_01", "C1_02", "C1_03", "C2_01", "C2_02", "C2_03", "C2_04", "C5_01", "C5_02"]   # 最初の9課題(追加分は add.sh)
trials = [(t, r) for t in ts for r in (1, 2, 3)]
random.Random(20261016).shuffle(trials)
for t, r in trials: print(t, r)
PY
while read t r; do SETTINGS=DEFAULT ./trial.py C $t $r > /dev/null 2>> logs/c2.err; echo "$t $r done" >> logs/c2.log; done < logs/c_order.txt
echo C_DONE >> logs/c2.log

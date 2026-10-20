#!/bin/bash
# 試行の束を流す。usage: run_set.sh NAME SEED "COND:TASK:REPS ..."   (順番はシード固定でシャッフル)
# 例: run_set.sh pilot 20261017 "Q:G01_01:1 L:G01_01:1"
cd "$(dirname "$0")"; NAME=$1; SEED=$2; shift 2
/opt/homebrew/bin/python3.13 - "$SEED" "$@" <<'PY' > logs/${NAME}_order.txt
import random, sys
seed = int(sys.argv[1]); items = []
for spec in " ".join(sys.argv[2:]).split():
    c, t, n = spec.split(":"); items += [(c, t, r) for r in range(1, int(n) + 1)]
random.Random(seed).shuffle(items)
for c, t, r in items: print(c, t, r)
PY
while read c t r; do
  [ -f logs/STOP ] && { echo "STOP があるので止める" >> logs/$NAME.log; break; }
  ./trial.py $c $t $r > /dev/null 2>> logs/$NAME.err; echo "$(date +%H:%M:%S) $c $t $r rc=$?" >> logs/$NAME.log
  # 費用の打ち切り(Q の累計 30 ドル)
  /opt/homebrew/bin/python3.13 -c "
import json,glob,sys
s=sum(json.load(open(p)).get('cost_usd',0) for p in glob.glob('$HOME/googleCloud/qwencode/runs/Q/*/r*/row.json'))
sys.exit(1 if s>30 else 0)" || { echo "費用が30ドルを超えたので止める" >> logs/$NAME.log; break; }
done < logs/${NAME}_order.txt
echo "${NAME}_DONE" >> logs/$NAME.log

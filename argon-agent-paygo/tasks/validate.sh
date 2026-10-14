#!/bin/bash
# 各課題で: 初期状態→判定(落ちるべき) / 模範解答→判定(通るべき) / 惜しい誤答→判定(落ちるべき)
cd "$(dirname "$0")"
V=~/googleCloud/argon/runs/validate; rm -rf $V; mkdir -p $V
OUT=validation.csv; [ $# -gt 0 ] && OUT=validation_partial.csv   # 一部だけ流したときは全体の結果を上書きしない
echo "task,empty,solve,nearmiss,ok" > $OUT
for t in ${@:-$(ls -d B*_[0-9]* | sort)}; do
  r=()
  for m in empty solve nearmiss; do
    W=$V/$t-$m; mkdir -p $W; chmod 777 $W
    ./dock.sh setup $t $W >/dev/null 2>$W.setup.err || { r+=(SETUPERR); continue; }
    [ $m != empty ] && { ./dock.sh $m $t $W >$W.$m.out 2>&1 || true; }
    j=$(./dock.sh judge $t $W 2>$W.judge.err | tail -1)
    echo "$j" > $W.judge.json
    r+=($(echo "$j" | python3 -c 'import sys,json;print("PASS" if json.loads(sys.stdin.read())["pass"] else "FAIL")' 2>/dev/null || echo ERR))
  done
  ok=$([ "${r[0]}" = FAIL ] && [ "${r[1]}" = PASS ] && [ "${r[2]}" = FAIL ] && echo yes || echo NO)
  echo "$t,${r[0]},${r[1]},${r[2]},$ok" | tee -a $OUT
done

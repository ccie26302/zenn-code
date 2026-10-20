#!/bin/bash
# Google Cloud の課題の3点検証(+別解): 初期状態は不合格、模範解答は合格、惜しい誤答は不合格、別解は合格
# 毎回、基準との差分を片付けてから次へ進む。usage: gvalidate.sh TASK...
cd "$(dirname "$0")"; H=../harness; V=~/googleCloud/qwencode/runs/gvalidate; mkdir -p $V
OUT=gvalidation_partial.csv; [ ! -f $OUT ] && echo "task,empty,solve,nearmiss,alt,ok" > $OUT
for t in "$@"; do
  r=()
  for m in empty solve nearmiss alt; do
    [ $m = alt ] && [ ! -f $t/alt.sh ] && { r+=(NA); continue; }
    ID=v$(openssl rand -hex 3); W=$V/$t-$m-$ID; mkdir -p $W; chmod 777 $W
    for k in 1 2 3 4 5 6 7 8 9; do d=$($H/gcp_state.sh diff $H/base | grep -v '^$'); [ -z "$d" ] && break; [ $k = 4 ] && $H/gcp_state.sh restore $H/base >/dev/null 2>&1; sleep 15; done
    [ -n "$d" ] && { echo "基準と違うので止める: $d"; exit 1; }
    ./gdock.sh setup $t $W $ID > $W.setup.log 2>&1 || { r+=(SETUPERR); $H/gcp_state.sh restore $H/base > $W.restore.log 2>&1; continue; }
    [ $m != empty ] && ./gdock.sh agent:$m $t $W $ID > $W.$m.log 2>&1
    [ -f $t/judge_exec.sh ] && ./gdock.sh agent:judge_exec $t $W $ID > $W.judge_exec.log 2>&1
    [ -f $t/sleep_before_judge ] && sleep $(cat $t/sleep_before_judge)
    j=$(./gdock.sh judge $t $W $ID 2> $W.judge.err | tail -1); echo "$j" > $W.judge.json
    r+=($(echo "$j" | python3 -c 'import sys,json;print("PASS" if json.loads(sys.stdin.read())["pass"] else "FAIL")' 2>/dev/null || echo ERR))
    $H/gcp_state.sh restore $H/base > $W.restore.log 2>&1
  done
  ok=$([ "${r[0]}" = FAIL ] && [ "${r[1]}" = PASS ] && [ "${r[2]}" = FAIL ] && { [ "${r[3]}" = PASS ] || [ "${r[3]}" = NA ]; } && echo yes || echo NO)
  echo "$t,${r[0]},${r[1]},${r[2]},${r[3]},$ok" | tee -a $OUT
done

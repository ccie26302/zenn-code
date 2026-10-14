#!/bin/bash
# v2.5 の追加の測定(探索的)
cd "$(dirname "$0")"
run(){ SETTINGS=$1 ./trial.py $2 $3 $4 > /dev/null 2>> logs/add.err; echo "$2 $3 $4 done" >> logs/add.log; }
for t in C2_05 C2_06 C2_07 C2_08 C2_09 C5_03 C5_04; do for r in 1 2 3; do run DEFAULT C $t $r; done; done
for r in 4 5 6 7 8 9 10; do run DEFAULT C C1_01 $r; run DEFAULT C C1_02 $r; done
for r in 1 2 3 4 5 6 7 8 9 10; do run DEFAULT C C1_06 $r; done
for r in 1 2 3 4 5; do run DEFAULT C C1_07 $r; done
for r in 1 2 3; do run NONE G1 B4_01 $r; done
echo ADD_DONE >> logs/add.log

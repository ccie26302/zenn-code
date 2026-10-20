#!/bin/bash
# L の試行中の Mac のシステム消費電力(ioreg の SystemPowerIn、mW)を2秒ごとに記録する
cd "$(dirname "$0")/../.."
p(){ ioreg -rw0 -c AppleSmartBattery | grep -o '"SystemPowerIn"=[0-9]*' | head -1 | cut -d= -f2; }
for i in $(seq 1 30); do echo "idle $(date +%s) $(p)"; sleep 2; done > notes/power/idle.txt
for t in M2_01 R_B2_01; do
  ( while true; do echo "$t $(date +%s) $(p)"; sleep 2; done ) >> notes/power/trial.txt & W=$!
  RUN_TAG=POWER_ harness/trial.py L $t 1 > notes/power/$t.row.json 2>/dev/null
  kill $W
done
echo DONE >> notes/power/trial.txt

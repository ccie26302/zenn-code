#!/bin/bash
# 本測定の実行(E3)。SA の作成から 1 時間たってから、伝播の確認をしてから流す
cd "$(dirname "$0")"
created=$(head -1 data/sa_created_at.txt)
start=$(( $(date -j -u -f %Y-%m-%dT%H:%M:%SZ "$created" +%s) + 3600 ))
while [ "$(date +%s)" -lt "$start" ]; do sleep 30; done
python3 scripts/probe.py
python3 scripts/e3.py --reps 3 --label main

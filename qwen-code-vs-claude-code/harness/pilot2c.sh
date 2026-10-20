#!/bin/bash
# 妥当性確認(17/17)のあと: C の予備試行 → Q の G/T の流し直し
cd "$(dirname "$0")"; L=logs/pilot2_chain.log
echo "--- C/Q pilot start $(date +%H:%M)" >> $L
./pilot_c.sh
TASKS=$(cd ../tasks && ls -d G[0-9]*_[0-9]* T[0-9]*_[0-9]* | sort); SPEC=""; for t in $TASKS; do SPEC="$SPEC Q:${t}:1"; done
RUN_TAG=PILOT2_ ./run_set.sh pilot2_q 20261021 $SPEC
echo PILOT2_ALL_DONE >> $L

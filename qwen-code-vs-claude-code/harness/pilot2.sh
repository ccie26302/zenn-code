#!/bin/bash
# 予備試行の見直しのあと: 陰性対照 → G/T の妥当性確認 → C の予備試行 → Q の G/T の流し直し
cd "$(dirname "$0")"; L=logs/pilot2_chain.log
./negcontrol_run.sh negcontrol_result_4.csv >> $L 2>&1
awk -F, 'NR>1 && $1!=$2' negcontrol_result_4.csv >> $L
(cd ../tasks && ./gvalidate.sh $(ls -d G[0-9]*_[0-9]* T[0-9]*_[0-9]* | sort) >> ../harness/$L 2>&1)
cp ../tasks/gvalidation_partial.csv ../tasks/gvalidation_v2.csv
if grep -q ",NO$\|基準と違う" ../tasks/gvalidation_v2.csv $L; then echo "VALIDATION_FAILED" >> $L; exit 1; fi
./pilot_c.sh
TASKS=$(cd ../tasks && ls -d G[0-9]*_[0-9]* T[0-9]*_[0-9]* | sort); SPEC=""; for t in $TASKS; do SPEC="$SPEC Q:${t}:1"; done
RUN_TAG=PILOT2_ ./run_set.sh pilot2_q 20261021 $SPEC
echo PILOT2_ALL_DONE >> $L

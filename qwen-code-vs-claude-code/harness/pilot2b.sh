#!/bin/bash
# pilot2.sh の続き(G06 の片付けの不具合を直したあと): 残りの G/T の妥当性確認 → C の予備試行 → Q の G/T の流し直し
cd "$(dirname "$0")"; L=logs/pilot2_chain.log
echo "--- resume $(date +%H:%M) after gcp_state fix" >> $L
REST=$(cd ../tasks && ls -d G[0-9]*_[0-9]* T[0-9]*_[0-9]* | sort | awk '$0 >= "G06_01"')
(cd ../tasks && ./gvalidate.sh $REST >> ../harness/$L 2>&1)
cp ../tasks/gvalidation_partial.csv ../tasks/gvalidation_v2.csv
if [ $(grep -c ",yes$" ../tasks/gvalidation_v2.csv) -ne 17 ] || tail -n +2 $L | grep -q "^基準と違う" ; then echo "VALIDATION_FAILED2" >> $L; exit 1; fi
./pilot_c.sh
TASKS=$(cd ../tasks && ls -d G[0-9]*_[0-9]* T[0-9]*_[0-9]* | sort); SPEC=""; for t in $TASKS; do SPEC="$SPEC Q:${t}:1"; done
RUN_TAG=PILOT2_ ./run_set.sh pilot2_q 20261021 $SPEC
echo PILOT2_ALL_DONE >> $L

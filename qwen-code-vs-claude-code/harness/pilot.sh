#!/bin/bash
# 予備試行: 全課題を各構成で1回(Q → L の順)。C はトークンが置かれてから別に流す
cd "$(dirname "$0")"
TASKS=$(cd ../tasks && ls -d [MDGTR]*_[0-9]* | sort)
SPEC_Q=""; SPEC_L=""
for t in $TASKS; do SPEC_Q="$SPEC_Q Q:${t}:1"; SPEC_L="$SPEC_L L:${t}:1"; done
RUN_TAG=PILOT_ ./run_set.sh pilot_q 20261018 $SPEC_Q
RUN_TAG=PILOT_ ./run_set.sh pilot_l 20261019 $SPEC_L
echo PILOT_ALL_DONE >> logs/pilot_chain.log

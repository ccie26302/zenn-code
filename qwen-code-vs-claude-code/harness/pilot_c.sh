#!/bin/bash
# 予備試行: 全課題を C で1回
cd "$(dirname "$0")"
TASKS=$(cd ../tasks && ls -d [MDGTR]*_[0-9]* | sort)
SPEC=""; for t in $TASKS; do SPEC="$SPEC C:${t}:1"; done
RUN_TAG=PILOT_ ./run_set.sh pilot_c 20261020 $SPEC

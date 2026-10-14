#!/bin/bash
# 予備試行: 各課題1回(費用の見積もりだけに使う)
cd "$(dirname "$0")"
for t in $(ls -d ../tasks/B*_0* | xargs -n1 basename | sort); do ./trial.py PILOT_DEFAULT $t 0 | cut -c1-400; done
echo PILOT_DONE

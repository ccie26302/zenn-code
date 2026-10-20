#!/bin/bash
# 惜しい誤答: SHIFT_JIS として変換する(①・髙・﨑・～・№ などの機種依存文字で失敗する)
cd "$1" && mkdir -p utf8 && for f in legacy/*.csv; do iconv -c -f SHIFT_JIS -t UTF-8 "$f" > utf8/$(basename "$f"); done

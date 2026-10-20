#!/bin/bash
# 別解: nkf
cd "$1" && mkdir -p utf8 && for f in legacy/*.csv; do nkf -Sw --cp932 "$f" > utf8/$(basename "$f"); done

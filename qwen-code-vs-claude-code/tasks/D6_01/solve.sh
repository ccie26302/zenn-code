#!/bin/bash
cd "$1" && mkdir -p utf8 && for f in legacy/*.csv; do iconv -f CP932 -t UTF-8 "$f" > utf8/$(basename "$f"); done

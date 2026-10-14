#!/bin/bash
# 惜しい誤答: zip に入っていないファイルを書き漏らす
cd "$1"
mkdir -p extracted && unzip -q -o delivery.zip -d extracted
cd extracted
while read -r h p; do
  if [ ! -f "$p" ]; then :
  elif [ "$(sha256sum "$p" | cut -d' ' -f1)" = "$h" ]; then echo "OK $p"
  else echo "NG $p"; fi
done < SHA256SUMS | sort -k2 > ../verify.txt

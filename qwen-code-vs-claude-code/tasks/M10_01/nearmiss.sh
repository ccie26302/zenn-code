#!/bin/bash
# 惜しい誤答: 可逆圧縮で書き出し、大きい画像が 100KB を超える
cd "$1" && mkdir -p out && for f in photos/*.jpg; do b=$(basename "$f" .jpg); for w in 320 640 1280; do cwebp -quiet -lossless -resize $w 0 "$f" -o out/$b-$w.webp; done; done

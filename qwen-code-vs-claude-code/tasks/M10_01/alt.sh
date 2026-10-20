#!/bin/bash
# 別解: ImageMagick で変換
cd "$1" && mkdir -p out && for f in photos/*.jpg; do b=$(basename "$f" .jpg); for w in 320 640 1280; do convert "$f" -resize ${w}x -quality 50 out/$b-$w.webp; done; done

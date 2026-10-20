#!/bin/bash
cd "$1" && mkdir -p out && for f in photos/*.jpg; do b=$(basename "$f" .jpg); for w in 320 640 1280; do cwebp -quiet -q 60 -resize $w 0 "$f" -o out/$b-$w.webp; done; done

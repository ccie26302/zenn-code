#!/bin/bash
# 惜しい誤答: 比率を保たずに引き伸ばす
cd "$1" && ffmpeg -y -v error -i video.mp4 -vf "scale=1080:1920" -c:a copy vertical.mp4

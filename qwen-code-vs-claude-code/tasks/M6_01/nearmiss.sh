#!/bin/bash
# 惜しい誤答: 最初の3秒だけを GIF にする
cd "$1" && ffmpeg -y -v error -t 3 -i demo.mp4 -vf "fps=8,scale=480:-1" demo.gif

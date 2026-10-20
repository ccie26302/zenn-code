#!/bin/bash
# 惜しい誤答: 再エンコードしてつなぐ
cd "$1" && ffmpeg -y -v error -i part1.mp4 -i part2.mp4 -i part3.mp4 -filter_complex "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[v][a]" -map "[v]" -map "[a]" full.mp4

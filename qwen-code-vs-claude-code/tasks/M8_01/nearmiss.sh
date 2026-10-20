#!/bin/bash
# 惜しい誤答: 映像だけ3倍速にして、音声は元のまま
cd "$1" && ffmpeg -y -v error -i lecture.mp4 -filter:v "setpts=PTS/3" -c:a aac fast.mp4

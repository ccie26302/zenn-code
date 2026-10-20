#!/bin/bash
# 惜しい誤答: ステレオのまま
cd "$1" && ffmpeg -y -v error -i video.mp4 -vn -ar 16000 -c:a pcm_s16le audio.wav

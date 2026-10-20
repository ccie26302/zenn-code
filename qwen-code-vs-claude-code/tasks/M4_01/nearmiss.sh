#!/bin/bash
# 惜しい誤答: 音声も AAC で作り直す
cd "$1" && ffmpeg -y -v error -i clip.mp4 -vf subtitles=subs.srt -c:a aac -b:a 96k burned.mp4

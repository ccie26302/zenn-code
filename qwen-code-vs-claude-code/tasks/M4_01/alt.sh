#!/bin/bash
# 別解: SRT を ASS に変換してから焼き込む
cd "$1" && ffmpeg -y -v error -i subs.srt subs.ass && ffmpeg -y -v error -i clip.mp4 -vf ass=subs.ass -c:a copy burned.mp4

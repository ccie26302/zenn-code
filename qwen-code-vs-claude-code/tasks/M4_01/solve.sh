#!/bin/bash
cd "$1" && ffmpeg -y -v error -i clip.mp4 -vf subtitles=subs.srt -c:a copy burned.mp4

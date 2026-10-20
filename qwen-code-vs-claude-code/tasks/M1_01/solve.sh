#!/bin/bash
cd "$1" && ffmpeg -y -v error -i video.mp4 -vn -ar 16000 -ac 1 -c:a pcm_s16le audio.wav

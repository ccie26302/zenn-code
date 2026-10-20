#!/bin/bash
cd "$1" && ffmpeg -y -v error -i lecture.mp4 -filter_complex "[0:v]setpts=PTS/3[v];[0:a]atempo=3.0[a]" -map "[v]" -map "[a]" fast.mp4

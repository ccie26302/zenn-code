#!/bin/bash
cd "$1" && printf "file %s\n" part1.mp4 part2.mp4 part3.mp4 > list.txt && ffmpeg -y -v error -f concat -safe 0 -i list.txt -c copy full.mp4

#!/bin/bash
cd "$1" && ffmpeg -y -v error -i video.mp4 -vf "scale=1080:-2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" -c:a copy vertical.mp4

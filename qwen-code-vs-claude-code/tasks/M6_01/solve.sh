#!/bin/bash
cd "$1" && ffmpeg -y -v error -i demo.mp4 -vf "fps=8,scale=480:-1:flags=lanczos,palettegen=max_colors=64" pal.png && ffmpeg -y -v error -i demo.mp4 -i pal.png -lavfi "fps=8,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse" demo.gif && rm pal.png

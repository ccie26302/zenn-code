#!/bin/bash
# 惜しい誤答: 放送の基準(-23 LUFS)で正規化する
cd "$1" && python3 /tasks/M7_01/twopass.py podcast.wav podcast_norm.wav -23

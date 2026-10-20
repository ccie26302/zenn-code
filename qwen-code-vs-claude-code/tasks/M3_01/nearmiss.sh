#!/bin/bash
# 惜しい誤答: 1秒以上の無音だけを削る(0.74秒の無音が残る)
cd "$1" && python3 /tasks/M3_01/cut.py talk.wav cut.wav 1.0

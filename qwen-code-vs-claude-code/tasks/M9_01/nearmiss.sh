#!/bin/bash
# 惜しい誤答: SRT ではなくテキストだけを meeting.srt に書く
cd "$1" && whisper-cli -m /opt/whisper-models/ggml-base.en.bin -f meeting.wav -otxt -of meeting -np >/dev/null 2>&1 && mv meeting.txt meeting.srt

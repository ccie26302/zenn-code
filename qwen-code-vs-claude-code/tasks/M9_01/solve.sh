#!/bin/bash
cd "$1" && whisper-cli -m /opt/whisper-models/ggml-base.en.bin -f meeting.wav -osrt -of meeting -np >/dev/null 2>&1

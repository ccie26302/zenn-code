# 素材を作る共通部品(合成の映像と、espeak-ng の読み上げ)
import os, subprocess
def sh(c, cwd): subprocess.run(c, shell=True, check=True, cwd=cwd, capture_output=True)
def video(cwd, name, sec=10, size="1280x720", rate=30, tone=440):
    sh("ffmpeg -y -f lavfi -i testsrc2=size=%s:rate=%d:duration=%d -f lavfi -i sine=frequency=%d:sample_rate=44100:duration=%d "
       "-ac 2 -c:v libx264 -pix_fmt yuv420p -preset veryfast -c:a aac -b:a 128k -shortest %s" % (size, rate, sec, tone, sec, name), cwd)
def speech(cwd, name, text, rate=16000, voice="en-us", gain_db=0):
    sh("espeak-ng -v %s -s 150 -w _tts.wav %s" % (voice, json_q(text)), cwd)
    sh("ffmpeg -y -i _tts.wav -ar %d -ac 1 -af volume=%sdB %s && rm _tts.wav" % (rate, gain_db, name), cwd)
def json_q(s):
    return "'" + s.replace("'", "") + "'"

import os, sys; sys.path.insert(0, "/tasks"); from mgen import speech, sh
LINES = ["Welcome back to the weekly cloud show.", "This week we look at cost controls and budgets.", "Thanks for listening, see you next week."]
if __name__ == "__main__":
    w = sys.argv[1]
    for i, t in enumerate(LINES): speech(w, "_s%d.wav" % i, t, rate=44100, gain_db=-14)
    open(os.path.join(w, "_l.txt"), "w").write("".join("file '_s%d.wav'\n" % i for i in range(len(LINES))))
    sh("ffmpeg -y -f concat -safe 0 -i _l.txt -c pcm_s16le podcast.wav && rm _*.wav _l.txt", w)

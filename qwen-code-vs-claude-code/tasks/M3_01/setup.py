import os, sys; sys.path.insert(0, "/tasks"); from mgen import speech, sh
LINES = ["Good morning everyone.", "Today we review the quarterly numbers.", "Sales grew in three regions.", "Please send questions by Friday."]
GAPS = [0.3, 1.2, 2.0, 0.8]          # 発話のあとの無音(秒)。0.5 以上が3つ
if __name__ == "__main__":
    w = sys.argv[1]; parts = []
    for i, (t, g) in enumerate(zip(LINES, GAPS)):
        speech(w, "_s%d.wav" % i, t); sh("ffmpeg -y -f lavfi -i anullsrc=r=16000:cl=mono -t %s _g%d.wav" % (g, i), w); parts += ["_s%d.wav" % i, "_g%d.wav" % i]
    open(os.path.join(w, "_l.txt"), "w").write("".join("file '%s'\n" % x for x in parts))
    sh("ffmpeg -y -f concat -safe 0 -i _l.txt -c pcm_s16le talk.wav && rm _*.wav _l.txt", w)

import os, sys; sys.path.insert(0, "/tasks"); from mgen import speech, sh
SCRIPT = ["Thank you all for joining the planning meeting.", "First, the storage migration is on schedule.", "Second, we will move the reports to a new bucket.",
          "Third, please review the access policy before Friday.", "Finally, the next meeting is on Monday morning."]
if __name__ == "__main__":
    w = sys.argv[1]
    for i, t in enumerate(SCRIPT): speech(w, "_s%d.wav" % i, t)
    open(os.path.join(w, "_l.txt"), "w").write("".join("file '_s%d.wav'\n" % i for i in range(len(SCRIPT))))
    sh("ffmpeg -y -f concat -safe 0 -i _l.txt -ar 16000 -ac 1 -c pcm_s16le meeting.wav && rm _*.wav _l.txt", w)

import os, sys; sys.path.insert(0, "/tasks"); from mgen import video
SRT = "1\n00:00:00,500 --> 00:00:02,500\nWelcome to the demo\n\n2\n00:00:03,500 --> 00:00:05,500\nThis line is burned in\n"
if __name__ == "__main__":
    w = sys.argv[1]; video(w, "clip.mp4", sec=7, size="1280x720"); open(os.path.join(w, "subs.srt"), "w").write(SRT)

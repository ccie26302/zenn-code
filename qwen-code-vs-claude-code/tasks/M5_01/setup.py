import sys; sys.path.insert(0, "/tasks"); from mgen import video
if __name__ == "__main__":
    for i, (s, t) in enumerate(((4, 330), (5, 440), (3, 550)), 1): video(sys.argv[1], "part%d.mp4" % i, sec=s, tone=t)

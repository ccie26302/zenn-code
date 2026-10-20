import sys; sys.path.insert(0, "/tasks"); from mgen import video
if __name__ == "__main__": video(sys.argv[1], "demo.mp4", sec=8, size="1280x720")

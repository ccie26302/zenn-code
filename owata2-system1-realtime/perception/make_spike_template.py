"""トゲ「△」1個のお手本(13×16)を、スタート地点の画面(穴の底のトゲが見えるコマ)から切り出す。
usage: python3 perception/make_spike_template.py [画面.png(既定 data/m1/bg.png)] → perception/spike_template.npy"""
import sys, os, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "data", "m1", "bg.png")
a = np.asarray(Image.open(src).convert("RGB")).astype(int).sum(axis=2)
T = (a[345:358, 187:203] < 300).astype(np.uint8)   # 1面スタート地点の画面で、穴の底のトゲの左端の1個
assert T.sum() > 30, "トゲが写っていない(スタート地点・カメラが動いていない画面を使う)"
np.save(os.path.join(HERE, "spike_template.npy"), T); print(T.shape, int(T.sum()))

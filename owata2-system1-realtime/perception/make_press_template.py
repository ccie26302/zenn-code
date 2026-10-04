"""2つ目の罠(下りてくる板の下向きトゲ「▼」)1個のお手本(9×15)を、板が画面に入っているコマから切り出す。
usage: python3 perception/make_press_template.py <画面.png> <▼の行の上端 y> <左端の▼の左 x> → perception/press_template.npy
例(検証で使ったコマ): 板の▼が y=171〜179、左端の▼が x=423〜437 にあるコマで `... 00150.png 171 423`"""
import sys, os, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
src, y, x = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
a = np.asarray(Image.open(src).convert("RGB")).astype(int).sum(axis=2)
T = (a[y:y + 9, x:x + 15] < 300).astype(np.uint8)
assert T.sum() > 40, "▼ が写っていない"
np.save(os.path.join(HERE, "press_template.npy"), T); print(T.shape, int(T.sum()))

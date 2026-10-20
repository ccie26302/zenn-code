import os, sys
from PIL import Image, ImageDraw, ImageFilter
import random
if __name__ == "__main__":
    d = os.path.join(sys.argv[1], "photos"); os.makedirs(d); rnd = random.Random(1010)
    for n in ("harbor", "forest", "street"):
        im = Image.new("RGB", (2400, 1600)); dr = ImageDraw.Draw(im)
        for y in range(1600): dr.line([(0, y), (2400, y)], fill=(40 + y // 12, 90 + y // 20, 160 - y // 16))      # 空のようなグラデーション
        for _ in range(60):
            x, y, r = rnd.randint(0, 2400), rnd.randint(500, 1600), rnd.randint(30, 220)
            dr.ellipse([x - r, y - r, x + r, y + r], fill=(rnd.randint(20, 200), rnd.randint(60, 180), rnd.randint(20, 120)))
        im = im.filter(ImageFilter.GaussianBlur(3))
        im = Image.blend(im, Image.effect_noise((2400, 1600), 12).convert("RGB"), 0.08)
        im.save(os.path.join(d, n + ".jpg"), quality=90)

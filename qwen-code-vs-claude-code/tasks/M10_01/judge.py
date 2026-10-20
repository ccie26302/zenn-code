import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done
from PIL import Image
w = sys.argv[1]; bad = []; n = 0
for b in ("harbor", "forest", "street"):
    for W in (320, 640, 1280):
        p = os.path.join(w, "out", "%s-%d.webp" % (b, W))
        if not os.path.exists(p): bad.append(("無い", p[-30:])); continue
        im = Image.open(p); n += 1
        if im.format != "WEBP" or im.width != W or abs(im.height - round(W * 1600 / 2400)) > 2: bad.append(("形式か大きさ", p[-25:], im.format, im.size))
        if os.path.getsize(p) > 100 * 1024: bad.append(("100KB 超", p[-25:], os.path.getsize(p)))
ck("9枚が指定どおり", n == 9 and not bad, bad[:3])
done()

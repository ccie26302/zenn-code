import os, random, sys
from PIL import Image
def gen():
    rnd = random.Random(1707); out = []
    for i in range(18):
        dt = None if i % 7 == 3 else "2025:%02d:%02d %02d:%02d:%02d" % (rnd.randint(1, 12), rnd.randint(1, 28), rnd.randint(0, 23), rnd.randint(0, 59), rnd.randint(0, 59))
        if i in (5, 6): dt = "2025:07:14 10:30:00"
        out.append(("IMG_%04d.JPG" % (100 + i * 3), dt, (rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255))))
    return out
if __name__ == "__main__":
    d = os.path.join(sys.argv[1], "camera"); os.makedirs(d)
    for n, dt, c in gen():
        im = Image.new("RGB", (64, 48), c); ex = Image.Exif()
        if dt: ex[0x8769] = {0x9003: dt}
        im.save(os.path.join(d, n), exif=ex, quality=90)

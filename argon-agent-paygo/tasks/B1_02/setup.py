import os, random, sys
def gen():
    rnd = random.Random(202); out = []
    for i in range(40):
        y, m, d = rnd.choice([2024, 2025]), rnd.randint(1, 12), rnd.randint(1, 28)
        if i % 9 == 0 and out:                       # 同じ日付をいくつか作る
            y, m, d = out[-1][2]
        f = rnd.choice(["%d-%d-%d", "%04d%02d%02d", "%04d_%02d_%02d", "%04d-%02d-%02d"]) % (y, m, d)
        name = rnd.choice(["IMG_%s_%03d", "photo %s (%d)", "%s_trip%02d", "DSC%s-%d"]) % (f, rnd.randint(0, 99)) + rnd.choice([".jpg", ".JPG", ".jpeg", ".JPEG"])
        if any(name == o[0] for o in out): continue
        out.append((name, ("img %d %s\n" % (i, name)).encode(), (y, m, d)))
    return out
if __name__ == "__main__":
    os.makedirs(os.path.join(sys.argv[1], "photos"))
    for n, data, _ in gen():
        open(os.path.join(sys.argv[1], "photos", n), "wb").write(data)

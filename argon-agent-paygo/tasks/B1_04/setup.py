import os, random, sys
def gen():
    rnd = random.Random(404); out = []
    for i in range(120):
        depth = rnd.randint(0, 6)
        d = "/".join(rnd.choice(["svc", "api", "web", "logs", "tmp", "build", "var", "app"]) + str(rnd.randint(0, 3)) for _ in range(depth))
        ext = rnd.choice([".log", ".log", ".txt", ".log.1", ".LOG", ".json"])
        size = rnd.choice([rnd.randint(0, 90000), rnd.randint(110000, 400000), 102400, 102399])
        mt = 1700000000 + rnd.randint(0, 50000000)
        out.append((os.path.join(d, "f%03d%s" % (i, ext)), size, mt))
    return out
if __name__ == "__main__":
    for rel, size, mt in gen():
        p = os.path.join(sys.argv[1], "project", rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(b"L" * size); os.utime(p, (mt, mt))

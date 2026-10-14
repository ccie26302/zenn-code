import gzip, os, random, sys
COMPS = ["auth", "billing", "api-gw", "worker", "db", "cache"]
def gen():
    rnd = random.Random(505); files = {}
    for fi in range(6):
        lines = []
        for i in range(9000):
            t = "2025-10-%02dT%02d:%02d:%02dZ" % (fi + 1, rnd.randint(0, 23), rnd.randint(0, 59), rnd.randint(0, 59))
            lv = rnd.choices(["INFO", "DEBUG", "WARN", "ERROR"], [60, 20, 12, 8])[0]
            c = rnd.choice(COMPS)
            code = rnd.choice(["E%03d" % rnd.randint(1, 12), "", "E%03d" % rnd.randint(1, 4)])
            msg = rnd.choice(["request failed %s", "timeout after 30s %s", "retrying %s", "user=%d ok" % rnd.randint(1, 999) + "%s"]) % ((" code=" + code) if code else "")
            r = rnd.random()
            if r < 0.004: line = t + " ERROR auth missing bracket" + (" E001" if rnd.random() < .5 else "")
            elif r < 0.007: line = "%s ERROR [%s" % (t, c)                                   # 途中で切れた行
            elif r < 0.009: line = ""                                                         # 空行
            elif r < 0.011: line = "Traceback (most recent call last): E777"
            elif r < 0.013: line = "%s error [%s] lower-case level E005" % (t, c)
            else: line = "%s %s [%s] %s" % (t, lv, c, msg)
            lines.append(line)
        files["app-%d.log%s" % (fi, ".gz" if fi % 2 else "")] = "\n".join(lines) + "\n"
    return files
if __name__ == "__main__":
    os.makedirs(os.path.join(sys.argv[1], "logs"))
    for n, txt in gen().items():
        p = os.path.join(sys.argv[1], "logs", n)
        if n.endswith(".gz"):
            with gzip.GzipFile(p, "wb", mtime=0) as f: f.write(txt.encode())
        else: open(p, "w").write(txt)

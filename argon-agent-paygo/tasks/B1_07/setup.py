import hashlib, io, os, random, sys, zipfile
def gen():
    rnd = random.Random(707); files = {}
    for i in range(25):
        files["%s/part_%02d.bin" % (rnd.choice(["data", "data/sub", "docs", "bin"]), i)] = bytes(rnd.getrandbits(8) for _ in range(rnd.randint(10, 3000)))
    sums = {p: hashlib.sha256(b).hexdigest() for p, b in files.items()}
    names = sorted(files)
    status = {p: "OK" for p in names}
    for p in names[3::9]: files[p] = files[p][:-1] + bytes([files[p][-1] ^ 1]); status[p] = "NG"   # 中身が壊れている
    for p in names[5::11]: del files[p]; status[p] = "MISSING"                                       # 入っていない
    return files, sums, status
if __name__ == "__main__":
    files, sums, _ = gen()
    with zipfile.ZipFile(os.path.join(sys.argv[1], "delivery.zip"), "w") as z:
        for p in sorted(files): z.writestr(zipfile.ZipInfo(p, (2025, 1, 1, 0, 0, 0)), files[p])
        z.writestr(zipfile.ZipInfo("SHA256SUMS", (2025, 1, 1, 0, 0, 0)), "".join("%s  %s\n" % (sums[p], p) for p in sorted(sums)))

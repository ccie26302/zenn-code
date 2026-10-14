import os, random, sys
def gen():
    rnd = random.Random(101)
    exts = ["jpg", "png", "JPG", "pdf", "docx", "txt", "xlsx", "csv", "PDF"]
    words = ["report", "invoice", "photo", "meeting", "budget", "draft", "scan", "memo"]
    out, seen = [], set()
    while len(out) < 200:
        e = rnd.choice(exts); w = rnd.choice(words)
        k = rnd.random()
        if k < 0.08:
            name = "%s_final_v%d.%s" % (w, rnd.randint(1, 9), e)          # 日付なし
        elif k < 0.12:
            name = "%s_%d.%s" % (w, rnd.randint(1000000, 9999999), e)     # 7桁(日付ではない)
        else:
            d = "%04d%02d%02d" % (rnd.choice([2024, 2025, 2026]), rnd.randint(1, 12), rnd.randint(1, 28))
            name = rnd.choice(["%s_%s.%s", "%s-%s-copy.%s", "IMG%s%s.%s"]) % ((w, d, e) if rnd.random() < .9 else ("", d, e))
        if name in seen: continue
        seen.add(name)
        out.append(("inbox/" + name, ("%s %d\n" % (name, rnd.random() * 1e9)).encode()))
    return out
if __name__ == "__main__":
    w = sys.argv[1]
    for rel, data in gen():
        p = os.path.join(w, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(data)

import os, random, sys
def gen():
    rnd = random.Random(303)
    dirs = ["", "2024", "2025/q1", "2025/q2", "old", "old/backup", "shared/team-a", "shared/team-b"]
    out, bodies = [], []
    for i in range(70):
        if i > 10 and rnd.random() < 0.3:
            body = rnd.choice(bodies)                  # 重複
        else:
            body = ("document %d\n" % i + "x" * rnd.randint(0, 300)).encode(); bodies.append(body)
        rel = os.path.join(rnd.choice(dirs), "%s_%02d%s" % (rnd.choice(["memo", "plan", "notes", "Copy of plan"]), i, rnd.choice([".txt", ".md", ".csv"])))
        out.append((rel, body))
    out.append(("same_size_a.txt", b"abcdef\n")); out.append(("same_size_b.txt", b"abcdeg\n"))   # 大きさだけ同じで中身は別
    return out
if __name__ == "__main__":
    for rel, b in gen():
        p = os.path.join(sys.argv[1], "docs", rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(b)

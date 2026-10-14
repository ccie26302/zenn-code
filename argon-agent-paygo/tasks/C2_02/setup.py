import os, sys
if __name__ == "__main__":
    for p in ["tmp/a.log", "tmp/cache/b.bin", "keep/important.txt"]:
        f = os.path.join(sys.argv[1], p); os.makedirs(os.path.dirname(f), exist_ok=True); open(f, "w").write("x\n")

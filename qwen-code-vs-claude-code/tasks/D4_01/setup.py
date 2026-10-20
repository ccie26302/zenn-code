import os, subprocess, sys
COUNTS = {"a": 12, "b": 7, "c": 9}
if __name__ == "__main__":
    d = os.path.join(sys.argv[1], "pdfs"); os.makedirs(d)
    for n, k in COUNTS.items():
        t = os.path.join(d, n + ".txt"); open(t, "w").write("\f".join("DOC-%s PAGE-%02d" % (n.upper(), i + 1) for i in range(k)))
        subprocess.run(["python3", "/tasks/D3_01/mkpdf.py", t, os.path.join(d, n + ".pdf")], check=True); os.remove(t)

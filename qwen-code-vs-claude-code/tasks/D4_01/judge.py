import glob, os, subprocess, sys; sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done; from setup import COUNTS
w = sys.argv[1]
exp = ["DOC-%s PAGE-%02d" % (n.upper(), i + 1) for n in ("a", "b", "c") for i in range(COUNTS[n])]
def pages(p):
    out = []
    n = int(subprocess.run(["qpdf", "--show-npages", p], capture_output=True, text=True).stdout.strip() or 0)
    for i in range(1, n + 1):
        out.append(" ".join(subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), p, "-"], capture_output=True, text=True).stdout.split()))
    return out
m = os.path.join(w, "merged.pdf")
if ck("merged.pdf がある", os.path.exists(m)):
    ck("merged.pdf が 28 ページで順番どおり", pages(m) == exp, pages(m)[:3])
parts = sorted(glob.glob(os.path.join(w, "split", "part-*.pdf")))
ck("split に part-01〜03 の3つ", [os.path.basename(x) for x in parts] == ["part-01.pdf", "part-02.pdf", "part-03.pdf"], [os.path.basename(x) for x in parts])
got = sum((pages(x) for x in parts), [])
ck("10・10・8 ページで順番どおり", [len(pages(x)) for x in parts] == [10, 10, 8] and got == exp, [len(pages(x)) for x in parts])
done()

import os, random, subprocess, sys
def gen():
    rnd = random.Random(1303); rows = []
    for i in range(1, 41):
        q = rnd.randint(1, 50); u = rnd.choice([120, 480, 1500, 2980, 12800])
        rows.append(("SKU-%04d" % (1000 + i * 7), rnd.choice(["Cable", "Adapter", "Monitor arm", "Keyboard", "Mouse pad"]) + " " + str(i), q, u, q * u))
    return rows
if __name__ == "__main__":
    w = sys.argv[1]; rows = gen()
    def page(rs, title):
        tr = "".join("<tr><td>%s</td><td>%s</td><td>%d</td><td>%s</td><td>%s</td></tr>" % (a, b, c, "{:,}".format(d), "{:,}".format(e)) for a, b, c, d, e in rs)
        return "<h2>%s</h2><table border=1><tr><th>SKU</th><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount</th></tr>%s</table>" % (title, tr)
    html = "<html><body style='font-family:sans-serif'>%s<div style='page-break-before:always'></div>%s</body></html>" % (page(rows[:22], "INVOICE No. 2025-118 (1/2)"), page(rows[22:], "INVOICE No. 2025-118 (2/2)"))
    # ImageMagick ではなく、ghostscript の無い環境でも作れるように、reportlab を使わずテキストから PDF を作る
    lines = []
    for i, part in enumerate((rows[:22], rows[22:])):
        lines.append("INVOICE No. 2025-118 (%d/2)" % (i + 1)); lines.append("SKU        Description          Qty  Unit price     Amount")
        for a, b, c, d, e in part: lines.append("%-10s %-20s %3d %11s %10s" % (a, b, c, "{:,}".format(d), "{:,}".format(e)))
        lines.append("\f")
    open(os.path.join(w, "_inv.txt"), "w").write("\n".join(lines))
    subprocess.run("cd %s && enscript -q -B -f Courier9 -o - _inv.txt 2>/dev/null | ps2pdf - invoice.pdf 2>/dev/null || python3 /tasks/D3_01/mkpdf.py _inv.txt invoice.pdf; rm -f _inv.txt" % w, shell=True, check=True)

# 別解: pypdf で
cd "$1" && python3 - <<'PY'
import os
from pypdf import PdfReader, PdfWriter
w = PdfWriter()
for n in ("a", "b", "c"):
    for p in PdfReader("pdfs/%s.pdf" % n).pages: w.add_page(p)
w.write("merged.pdf"); r = PdfReader("merged.pdf"); os.makedirs("split", exist_ok=True)
for k in range(0, len(r.pages), 10):
    x = PdfWriter(); [x.add_page(p) for p in r.pages[k:k + 10]]; x.write("split/part-%02d.pdf" % (k // 10 + 1))
PY

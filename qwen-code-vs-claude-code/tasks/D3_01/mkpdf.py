# 文字だけの PDF を手で組み立てる(外部の道具なし)。\f でページを分ける
import sys
txt = open(sys.argv[1]).read().split("\f"); pages = [p.strip("\n").split("\n") for p in txt if p.strip()]
objs = []; kids = []
def add(s): objs.append(s); return len(objs)
font = add("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
pages_id_placeholder = add("")
for lines in pages:
    body = "BT /F1 9 Tf 40 800 Td 11 TL " + " ".join("(%s) Tj T*" % l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for l in lines) + " ET"
    c = add("<< /Length %d >>\nstream\n%s\nendstream" % (len(body), body))
    kids.append(add("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>" % (pages_id_placeholder, font, c)))
objs[pages_id_placeholder - 1] = "<< /Type /Pages /Kids [%s] /Count %d >>" % (" ".join("%d 0 R" % k for k in kids), len(kids))
cat = add("<< /Type /Catalog /Pages %d 0 R >>" % pages_id_placeholder)
out = "%PDF-1.4\n"; offs = []
for i, o in enumerate(objs, 1): offs.append(len(out.encode("latin-1"))); out += "%d 0 obj\n%s\nendobj\n" % (i, o)
x = len(out.encode("latin-1")); out += "xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + "".join("%010d 00000 n \n" % o for o in offs)
out += "trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, cat, x)
open(sys.argv[2], "wb").write(out.encode("latin-1"))

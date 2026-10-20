import os, re, sys
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done, files
from setup import gen
w = sys.argv[1]
KIND = {"jpg": "images", "png": "images", "pdf": "docs", "docx": "docs", "txt": "docs", "xlsx": "sheets", "csv": "sheets"}
expect = {}
for rel, data in gen():
    name = os.path.basename(rel)
    k = KIND[name.rsplit(".", 1)[1].lower()]
    m = re.search(r"(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)", name)
    ym = "%s-%s" % (m.group(1), m.group(2)) if m else "unknown"
    expect["sorted/%s/%s/%s" % (k, ym, name)] = data
inbox = os.path.join(w, "inbox")
ck("inbox が空", os.path.isdir(inbox) and not os.listdir(inbox) or not os.path.exists(inbox), os.listdir(inbox)[:5] if os.path.isdir(inbox) else "")
got = files(os.path.join(w, "sorted")) if os.path.isdir(os.path.join(w, "sorted")) else []
got = ["sorted/" + g for g in got]
miss = [e for e in expect if e not in got]
extra = [g for g in got if g not in expect]
ck("全ファイルが正しい場所にある", not miss, miss[:5])
ck("余計なファイルがない", not extra, extra[:5])
bad = [e for e in expect if e in got and open(os.path.join(w, e), "rb").read() != expect[e]]
ck("中身が変わっていない", not bad, bad[:5])
done()

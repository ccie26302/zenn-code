import csv, datetime, os, sys
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done
from setup import gen
w = sys.argv[1]
exp = sorted((r, s, datetime.datetime.fromtimestamp(m, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")) for r, s, m in gen() if r.endswith(".log") and s >= 102400)
p = os.path.join(w, "report.csv")
if ck("report.csv がある", os.path.exists(p)):
    rows = list(csv.reader(open(p, newline="", encoding="utf-8-sig")))
    ck("ヘッダー", rows and [c.strip() for c in rows[0]] == ["path", "size_bytes", "mtime"], rows[:1])
    body = [(r[0].strip(), int(r[1]), r[2].strip()) for r in rows[1:] if r]
    ck("対象の集合", set(b[0] for b in body) == set(e[0] for e in exp), sorted(set(b[0] for b in body) ^ set(e[0] for e in exp))[:5])
    ck("サイズと日時", body == exp or sorted(body) == exp, [b for b in body if b not in exp][:3])
    ck("path の昇順", [b[0] for b in body] == sorted(b[0] for b in body))
done()

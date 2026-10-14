import os, sqlite3, sys
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done
from setup import gen
w = sys.argv[1]
p = os.path.join(w, "out/data.db")
INTCOLS = {"users": {"id", "age"}, "orders": {"order_id", "user_id", "amount"}, "stores": set()}
if ck("out/data.db がある", os.path.exists(p)):
    con = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
    tabs = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    ck("テーブルがそろっている", {"users", "orders", "stores"} <= tabs, tabs)
    for t, rows in gen().items():
        if t not in tabs: continue
        cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)]
        ck("%s: 列名" % t, cols == rows[0], cols)
        got = con.execute("SELECT * FROM %s" % t).fetchall()
        exp = [tuple(v if rows[0][i] in INTCOLS[t] else str(v) for i, v in enumerate(r)) for r in rows[1:]]
        ck("%s: 行数(ヘッダーを含まない)" % t, len(got) == len(exp), len(got))
        ck("%s: 値と型" % t, sorted(map(repr, got)) == sorted(map(repr, exp)), [g for g in got if g not in exp][:2])
done()

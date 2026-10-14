import os, sys
sys.path.insert(0, "/tasks")
from jlib import write
MANAGE = '''"""売上データの小さな管理ツール"""
import argparse, csv, json, os, sqlite3, sys

DB = "app.db"


def initdb(a):
    con = sqlite3.connect(DB)
    con.execute("DROP TABLE IF EXISTS sales")
    con.execute("CREATE TABLE sales (store TEXT, month TEXT, amount INTEGER)")
    con.commit(); print("initialized", DB)


def do_import(a):
    if not os.path.exists(DB):
        sys.exit("error: database not initialized. run: python3 manage.py initdb")
    con = sqlite3.connect(DB)
    rows = [(r["store"], r["month"], int(r["amount"])) for r in csv.DictReader(open(a.csv, encoding="utf-8"))]
    con.executemany("INSERT INTO sales VALUES (?, ?, ?)", rows); con.commit(); print("imported", len(rows))


def export(a):
    con = sqlite3.connect(DB)
    out = {s: t for s, t in con.execute("SELECT store, SUM(amount) FROM sales GROUP BY store ORDER BY store")}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump({"format": a.format, "totals": out}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", a.out)


p = argparse.ArgumentParser(prog="manage.py")
sp = p.add_subparsers(dest="cmd", required=True)
sp.add_parser("initdb", help="データベースを作り直す(旧名 init-db は v2 で廃止)").set_defaults(f=initdb)
x = sp.add_parser("import", help="CSV を取り込む"); x.add_argument("csv"); x.set_defaults(f=do_import)
x = sp.add_parser("export", help="店舗ごとの合計を JSON に書く")
x.add_argument("--out", required=True, help="出力先(v2 から必須のオプション)")
x.add_argument("--format", default="v2")
x.set_defaults(f=export)
a = p.parse_args(); a.f(a)
'''
README = '''# sales-tool

## セットアップ

1. データベースを作ります。

```
python3 manage.py init-db
```

2. サンプルのデータを取り込みます。

```
python3 manage.py import data/sales.csv
```

3. 店舗ごとの合計を書き出します。

```
python3 manage.py export out/summary.json
```
'''
CSV = "store,month,amount\n渋谷,2026-01,1200\n梅田,2026-01,900\n渋谷,2026-02,1300\n天神,2026-02,400\n梅田,2026-02,1000\n"
if __name__ == "__main__": write(sys.argv[1], {"manage.py": MANAGE, "README.md": README, "data/sales.csv": CSV})

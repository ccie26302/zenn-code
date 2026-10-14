import os, random, sys
sys.path.insert(0, "/tasks")
from jlib import write
def gen():
    rnd = random.Random(707)
    users = [["id", "name", "age", "zip"]] + [[i, "user%02d" % i, rnd.randint(18, 80), "%03d-%04d" % (rnd.randint(100, 999), rnd.randint(0, 9999))] for i in range(1, 41)]
    orders = [["order_id", "user_id", "amount", "note"]] + [[1000 + k, rnd.randint(1, 40), rnd.randint(100, 90000), rnd.choice(["", "gift", "急ぎ, 午前指定", '"引用"あり'])] for k in range(120)]
    stores = [["code", "name", "opened"]] + [["S%02d" % i, "店舗%d" % i, "20%02d-04-01" % (10 + i)] for i in range(1, 9)]
    return {"users": users, "orders": orders, "stores": stores}
DOC = '''# CSV の取り込み手順

sqlite3 コマンドの .import を使います。

```
mkdir -p out
sqlite3 out/data.db ".import --csv data/users.csv users"
sqlite3 out/data.db ".import --csv data/orders.csv orders"
sqlite3 out/data.db ".import --csv data/stores.csv stores"
```
'''
if __name__ == "__main__":
    import csv, io
    files = {"docs/import.md": DOC}
    for n, rows in gen().items():
        s = io.StringIO(); csv.writer(s, lineterminator="\n").writerows(rows); files["data/%s.csv" % n] = s.getvalue()
    write(sys.argv[1], files)

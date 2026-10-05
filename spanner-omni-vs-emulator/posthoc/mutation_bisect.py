"""事後の検証(事前登録の外): 1コミットのミューテーション数の上限を、列数の違う2つのテーブルで二分探索する。
Big8(主キー＋7列)と One(主キーだけ)の行数で境界を出し、何を数えているかを推定する。usage: python posthoc/mutation_bisect.py TARGET"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "harness"))
os.environ["SPANNER_DISABLE_BUILTIN_METRICS"] = "true"
from targets import database
t = sys.argv[1]; db = database(t, "cmp2", create=False)
def clean():
    for tb in ("Big8", "One"):
        db.execute_partitioned_dml(f"DELETE FROM {tb} WHERE true")
def ok(table, n):
    cols = ["id"] + ([f"c{k}" for k in range(1, 8)] if table == "Big8" else [])
    try:
        db.run_in_transaction(lambda tx: tx.insert(table, cols, [[i] + ["x"] * (len(cols) - 1) for i in range(n)])); r = True
    except Exception:  # noqa: BLE001
        r = False
    clean(); return r
for table, lo, hi in [("Big8", 1, 40000), ("One", 1, 400000)]:
    if ok(table, hi):
        print(t, table, "上限が", hi, "行より大きい"); continue
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if ok(table, mid) else (lo, mid)
    print(t, table, "max rows:", lo, "| cols:", 8 if table == "Big8" else 1, "| rows*cols:", lo * (8 if table == "Big8" else 1), "| rows*(cols-1):", lo * (7 if table == "Big8" else 0))

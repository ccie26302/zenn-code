"""事後の検証(事前登録の外): BYTES 1セルで受理される最大の大きさ(復号後のバイト数)を二分探索する。usage: python posthoc/cell_bisect.py TARGET"""
import sys, os, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "harness"))
os.environ["SPANNER_DISABLE_BUILTIN_METRICS"] = "true"
from targets import database
t = sys.argv[1]; db = database(t, "cmp2", create=False)
def ok(n):
    try:
        db.run_in_transaction(lambda tx: tx.insert_or_update("Blob", ["id", "b"], [[1, base64.b64encode(b"\0" * n)]])); return True
    except Exception:  # noqa: BLE001
        return False
lo, hi = 10 * 1024 * 1024 * 3 // 4 + 3, 10 * 1024 * 1024 - 1   # lo は受理、hi は拒否を確認済み
assert ok(lo) and not ok(hi)
while hi - lo > 1:
    mid = (lo + hi) // 2
    lo, hi = (mid, hi) if ok(mid) else (lo, mid)
print(t, "max accepted bytes:", lo, "| first rejected:", hi, "| 10MiB - max =", 10 * 1024 * 1024 - lo)

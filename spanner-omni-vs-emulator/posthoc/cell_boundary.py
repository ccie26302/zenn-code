"""事後の検証(事前登録の外): BYTES 列1セルの上限は、復号後の大きさか、base64 の長さか。
usage: python posthoc/cell_boundary.py TARGET"""
import sys, os, base64, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "harness"))
os.environ["SPANNER_DISABLE_BUILTIN_METRICS"] = "true"
from targets import database
t = sys.argv[1]; db = database(t, "cmp2", create=False)
L = 10 * 1024 * 1024
out = {}
for name, n in [("dec_7.5MiB(=b64 10MiB)", L * 3 // 4), ("dec_7.5MiB+3(=b64 10MiB+4)", L * 3 // 4 + 3), ("dec_10MiB-1", L - 1)]:
    try:
        db.run_in_transaction(lambda tx: tx.insert_or_update("Blob", ["id", "b"], [[1, base64.b64encode(b"\0" * n)]])); out[name] = "OK"
    except Exception as e:  # noqa: BLE001
        out[name] = f"{getattr(e, 'grpc_status_code', type(e).__name__)}: {str(e)[:90]}"
print(t, json.dumps(out, ensure_ascii=False))

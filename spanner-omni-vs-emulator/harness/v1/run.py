"""usage: python run.py TARGET [K] [CASE...]   TARGET = emu | omni | cloud
各テストを K 回(既定5)流し、生データを data/raw_<TARGET>.jsonl に追記する。A13(再起動)は restart.py で別に流す。"""
import sys, json, time, datetime, platform, importlib.metadata as md, os
sys.path.insert(0, os.path.dirname(__file__))
from targets import database
from cases import CASES, SCHEMA, seed

target = sys.argv[1]; K = int(sys.argv[2]) if len(sys.argv) > 2 else 5
names = sys.argv[3:] or sorted(CASES, key=lambda n: (n[0], int(n[1:])))
out = os.path.join(os.path.dirname(__file__), "..", "data", f"raw_{target}.jsonl")
os.makedirs(os.path.dirname(out), exist_ok=True)
meta = {"lib": md.version("google-cloud-spanner"), "python": platform.python_version(), "started": datetime.datetime.now().isoformat()}
db = database(target, "cmp", SCHEMA)
seed(db)
with open(out, "a") as f:
    for n in names:
        for rep in range(K):
            ctx = {"target": target, "rep": rep}
            t0 = time.time()
            try:
                r = CASES[n](db, ctx)
            except Exception as e:  # noqa: BLE001 - ハーネス側の失敗も記録
                r = {"status": "HARNESS_" + type(e).__name__, "value": None, "message": str(e)[:200]}
            rec = {"case": n, "target": target, "rep": rep, **r, **meta,
                   "at": datetime.datetime.now().isoformat()}
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n"); f.flush()
            print(n, rep, r["status"], json.dumps(r["value"], ensure_ascii=False, default=str)[:120], r["message"][:80].replace("\n", " "))
            if n in ("C2", "C3", "C11", "A10"):
                seed(db)

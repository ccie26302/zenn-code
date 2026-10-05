"""1ラウンド分: python run_v2.py TARGET ROUND [CASE...]
並行性のテスト(A1〜A3)は1ラウンド6回、それ以外は1回。5ラウンドで K=30 と K=5。生データは data/v2/raw_<TARGET>.jsonl に追記。
性能は測らない(所要時間を記録しない)。"""
import sys, json, datetime, platform, importlib.metadata as md, os
sys.path.insert(0, os.path.dirname(__file__))
from targets import database
from cases_v2 import CASES, ORDER, SCHEMA, CONCURRENCY, seed

target, rnd = sys.argv[1], int(sys.argv[2]); names = sys.argv[3:] or ORDER
out = os.path.join(os.path.dirname(__file__), "..", "data", "v2", f"raw_{target}.jsonl")
os.makedirs(os.path.dirname(out), exist_ok=True)
meta = {"lib": md.version("google-cloud-spanner"), "python": platform.python_version(), "run_id": os.environ.get("RUN_ID", "dev"),
        "omni_digest": os.environ.get("OMNI_DIGEST"), "emu_digest": os.environ.get("EMU_DIGEST")}
TRANSIENT = {"UNAVAILABLE", "RESOURCE_EXHAUSTED", "UNAUTHENTICATED"}   # 事前登録: その回は無効、1回だけ流し直す
SKIP = {("cloud", "B3")}                                               # 事前登録: Data Boost は Cloud で流さない(課金の可能性)
db = database(target, "cmp2", SCHEMA); seed(db)
with open(out, "a") as f:
    for n in names:
        reps = 6 if n in CONCURRENCY else 1
        for i in range(reps):
            rep = rnd * reps + i; ctx = {"target": target, "rep": rep, "run": meta["run_id"]}
            if (target, n) in SKIP:
                r = {"status": "SKIPPED_BY_PREREG", "value": None, "message": ""}
            else:
                for attempt in range(2):
                    try:
                        r = CASES[n](db, ctx)
                    except Exception as e:  # noqa: BLE001 - ハーネス側の失敗も記録
                        r = {"status": "HARNESS_" + type(e).__name__, "value": None, "message": str(e)[:200]}
                    if r["status"] not in TRANSIENT:
                        break
                    r["invalid_transient_first"] = True
            f.write(json.dumps({"case": n, "target": target, "round": rnd, "rep": rep, **r, **meta, "at": datetime.datetime.now().isoformat()},
                               ensure_ascii=False, default=str) + "\n"); f.flush()
            print(target, n, rep, r["status"], json.dumps(r["value"], ensure_ascii=False, default=str)[:150], (r["message"] or "")[:70].replace("\n", " "), flush=True)
            if n in ("C2", "C3", "C11", "A10", "A7"):
                seed(db)

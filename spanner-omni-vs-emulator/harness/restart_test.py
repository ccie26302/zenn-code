"""A13: 書き込み後にサーバを止めて再起動し、行が残るか(emu / omni のみ。基準は仕様=永続化されること)。
usage: python restart_test.py TARGET MODE REP   MODE = graceful | kill9"""
import sys, os, subprocess, time, json, datetime
sys.path.insert(0, os.path.dirname(__file__))
from targets import database
target, mode, rep = sys.argv[1], sys.argv[2], int(sys.argv[3])
cont = {"emu": "spanneremu", "omni": "spanneromni"}[target]
db = database(target, "restart", ["CREATE TABLE R (id INT64 NOT NULL) PRIMARY KEY (id)"])
key = rep * 10 + (1 if mode == "kill9" else 0)        # graceful と kill9 で行を分ける(前回の行で誤って「残った」としないため)
db.run_in_transaction(lambda tx: tx.insert_or_update("R", ["id"], [[key]]))
subprocess.run((["docker", "kill", cont] if mode == "kill9" else ["docker", "stop", "-t", "120", cont]), check=True, capture_output=True)
subprocess.run(["docker", "start", cont], check=True, capture_output=True)
res = {"status": None}
for _ in range(120):
    try:
        db2 = database(target, "restart", create=False)
        if not db2.exists():
            res = {"status": "OK", "value": {"db_exists": False, "row": False}}; break
        with db2.snapshot() as s:
            rows = [r[0] for r in s.execute_sql("SELECT id FROM R")]
        res = {"status": "OK", "value": {"db_exists": True, "row": key in rows}}; break
    except Exception as e:  # noqa: BLE001
        res = {"status": type(e).__name__, "value": None, "message": str(e)[:200]}; time.sleep(2)
out = os.path.join(os.path.dirname(__file__), "..", "data", "v2", f"raw_restart.jsonl")
with open(out, "a") as f:
    f.write(json.dumps({"case": "A13", "target": target, "mode": mode, "rep": rep, **res, "at": datetime.datetime.now().isoformat()}, ensure_ascii=False) + "\n")
print(target, mode, rep, res)

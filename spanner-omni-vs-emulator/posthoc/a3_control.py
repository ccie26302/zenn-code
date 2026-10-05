"""事後の検証(事前登録の外): A3 で Omni(とエミュレータ)のトランザクションが再試行され、本番では再試行されなかった件の切り分け。
DDL を出さずに同じトランザクション(0.5秒ごとに6回読んでから更新)を N 回流し、再試行が起きるかを見る。
usage: python posthoc/a3_control.py TARGET N"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "harness"))
os.environ["SPANNER_DISABLE_BUILTIN_METRICS"] = "true"
from targets import database
from cases_v2 import SER
t, N = sys.argv[1], int(sys.argv[2])
db = database(t, "cmp2", create=False)
db.run_in_transaction(lambda tx: tx.insert_or_update("Acc", ["id", "v"], [[1, 0]]))
retried = 0
for i in range(N):
    rec = {"attempts": 0}
    def fn(tx):
        rec["attempts"] += 1
        for _ in range(6):
            list(tx.execute_sql("SELECT v FROM Acc WHERE id=1")); time.sleep(0.5)
        tx.update("Acc", ["id", "v"], [[1, i]])
    db.run_in_transaction(fn, **SER)
    retried += rec["attempts"] > 1
print(t, "no_ddl", "N", N, "retried", retried)

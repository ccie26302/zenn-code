"""PREREGISTRATION.md のテスト。各関数は (db, ctx) を受け取り {"status", "value", "message"} を返す。
status は "OK" か gRPC のステータスコード名。value は Cloud と比べる正規化した結果。"""
import threading, time, datetime, json, decimal
from google.api_core import exceptions as gex
from google.cloud.spanner_v1 import param_types

SCHEMA = [
    "CREATE TABLE Acc (id INT64 NOT NULL, v INT64) PRIMARY KEY (id)",
    "CREATE TABLE Big (id INT64 NOT NULL, c1 STRING(10), c2 STRING(10), c3 STRING(10), c4 STRING(10), c5 STRING(10), "
    "c6 STRING(10), c7 STRING(10), c8 STRING(10), c9 STRING(10), c10 STRING(10)) PRIMARY KEY (id)",
    "CREATE TABLE Parent (id INT64 NOT NULL) PRIMARY KEY (id)",
    "CREATE TABLE Child (id INT64 NOT NULL, pid INT64, CONSTRAINT FK_Child_Parent FOREIGN KEY (pid) REFERENCES Parent (id)) PRIMARY KEY (id)",
    "CREATE TABLE Chk (id INT64 NOT NULL, x INT64, CONSTRAINT x_pos CHECK (x > 0)) PRIMARY KEY (id)",
    "CREATE TABLE Ts (id INT64 NOT NULL, t TIMESTAMP OPTIONS (allow_commit_timestamp = true)) PRIMARY KEY (id)",
    "CREATE TABLE Gen (id INT64 NOT NULL, a INT64, b INT64 AS (a * 2) STORED) PRIMARY KEY (id)",
    "CREATE TABLE Typ (id INT64 NOT NULL, j JSON, n NUMERIC) PRIMARY KEY (id)",
    "CREATE TABLE Stale (id INT64 NOT NULL) PRIMARY KEY (id)",
    "CREATE SEQUENCE Sq OPTIONS (sequence_kind = 'bit_reversed_positive')",
    "CREATE TABLE SeqT (id INT64 NOT NULL DEFAULT (GET_NEXT_SEQUENCE_VALUE(SEQUENCE Sq)), x INT64) PRIMARY KEY (id)",
    "CREATE TABLE Person (id INT64 NOT NULL, name STRING(20)) PRIMARY KEY (id)",
    "CREATE TABLE Knows (id INT64 NOT NULL, dst INT64 NOT NULL) PRIMARY KEY (id, dst)",
    "CREATE PROPERTY GRAPH G NODE TABLES (Person) EDGE TABLES (Knows SOURCE KEY (id) REFERENCES Person (id) DESTINATION KEY (dst) REFERENCES Person (id) LABEL Knows)",
    "CREATE TABLE Doc (id INT64 NOT NULL, body STRING(MAX), tok TOKENLIST AS (TOKENIZE_FULLTEXT(body)) HIDDEN, "
    "tok_ja TOKENLIST AS (TOKENIZE_FULLTEXT(body, language_tag => 'ja')) HIDDEN) PRIMARY KEY (id)",
    "CREATE SEARCH INDEX DocIdx ON Doc (tok, tok_ja)",
    "CREATE TABLE Item (id INT64 NOT NULL, cat STRING(10), price INT64) PRIMARY KEY (id)",
    "CREATE INDEX ItemByCat ON Item (cat)",
]


def err(e):
    code = getattr(e, "grpc_status_code", None)
    name = code.name if code is not None else type(e).__name__
    return {"status": name, "value": None, "message": str(e)[:200]}


def ok(value=None):
    return {"status": "OK", "value": value, "message": ""}


def run(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - 結果として記録する
        return err(e)


def reset(db, tables):
    def fn(tx):
        for t in tables:
            tx.execute_update(f"DELETE FROM {t} WHERE true")
    db.run_in_transaction(fn)


def seed(db):
    """テストで使う固定データ(冪等)。"""
    reset(db, ["Child", "Parent", "Item", "Person", "Knows", "Doc"])
    def fn(tx):
        tx.insert("Parent", ["id"], [[1], [2]])
        tx.insert("Item", ["id", "cat", "price"], [[i, f"c{i % 10}", i] for i in range(300)])
        tx.insert("Person", ["id", "name"], [[1, "alice"], [2, "bob"], [3, "carol"]])
        tx.insert("Knows", ["id", "dst"], [[1, 2], [2, 3]])
        tx.insert("Doc", ["id", "body"], [[1, "Spanner database engine"], [2, "分散データベースのエンジン"], [3, "running databases"]])
    db.run_in_transaction(fn)


# ---------- 並行性 ----------
def _two(db, body_a, body_b, start_gap=0.0):
    rec = {"A": {"calls": 0, "read": []}, "B": {"calls": 0, "read": []}}
    errs = {}
    def go(name, body):
        def fn(tx):
            rec[name]["calls"] += 1
            body(tx, rec[name])
        try:
            db.run_in_transaction(fn)
        except Exception as e:  # noqa: BLE001
            errs[name] = err(e)["status"]
    ta = threading.Thread(target=go, args=("A", body_a)); tb = threading.Thread(target=go, args=("B", body_b))
    ta.start(); time.sleep(start_gap); tb.start(); ta.join(); tb.join()
    return rec, errs


def A1(db, ctx):
    """別々の行の更新2本。性質: どちらも1回で済むか(余計な中断がないか)。"""
    reset(db, ["Acc"]); db.run_in_transaction(lambda tx: tx.insert("Acc", ["id", "v"], [[1, 0], [2, 0]]))
    def body(k):
        def b(tx, r):
            v = list(tx.execute_sql("SELECT v FROM Acc WHERE id=@k", params={"k": k}, param_types={"k": param_types.INT64}))[0][0]
            r["read"].append(v); time.sleep(1.0); tx.update("Acc", ["id", "v"], [[k, v + 1]])
        return b
    rec, errs = _two(db, body(1), body(2), 0.1)
    with db.snapshot() as s:
        final = sorted(tuple(r) for r in s.execute_sql("SELECT id, v FROM Acc ORDER BY id"))
    return ok({"retried": any(rec[n]["calls"] > 1 for n in "AB"), "final": final, "errs": errs, "calls": [rec["A"]["calls"], rec["B"]["calls"]]})


def A2(db, ctx):
    """同じ行の read-modify-write 2本。性質: 最終値=2(更新が失われない)、両方が同じ値0を読んだ試行があったか。"""
    reset(db, ["Acc"]); db.run_in_transaction(lambda tx: tx.insert("Acc", ["id", "v"], [[1, 0]]))
    def b(tx, r):
        v = list(tx.execute_sql("SELECT v FROM Acc WHERE id=1"))[0][0]
        r["read"].append(v); time.sleep(1.0); tx.update("Acc", ["id", "v"], [[1, v + 1]])
    rec, errs = _two(db, b, b, 0.1)
    with db.snapshot() as s:
        final = list(s.execute_sql("SELECT v FROM Acc WHERE id=1"))[0][0]
    both_read_zero = rec["A"]["read"][:1] == [0] and rec["B"]["read"][:1] == [0]
    return ok({"final": final, "both_read_initial": both_read_zero, "retried": any(rec[n]["calls"] > 1 for n in "AB"), "errs": errs,
               "calls": [rec["A"]["calls"], rec["B"]["calls"]]})


def A3(db, ctx):
    """読み書きトランザクション(2秒)の最中に、別テーブルの DDL を出す。性質: トランザクションが再試行されたか、DDL が成功したか。"""
    reset(db, ["Acc"]); db.run_in_transaction(lambda tx: tx.insert("Acc", ["id", "v"], [[1, 0]]))
    rec = {"calls": 0}; out = {}
    def fn(tx):
        rec["calls"] += 1
        list(tx.execute_sql("SELECT v FROM Acc WHERE id=1")); time.sleep(2.0); tx.update("Acc", ["id", "v"], [[1, 1]])
    def txn():
        try:
            db.run_in_transaction(fn); out["txn"] = "OK"
        except Exception as e:  # noqa: BLE001
            out["txn"] = err(e)["status"]
    t = threading.Thread(target=txn); t.start(); time.sleep(0.5)
    name = f"DdlT{ctx['rep']}"
    try:
        db.update_ddl([f"CREATE TABLE {name} (id INT64 NOT NULL) PRIMARY KEY (id)"]).result(600); out["ddl"] = "OK"
    except Exception as e:  # noqa: BLE001
        out["ddl"] = err(e)["status"]
    t.join()
    try:
        db.update_ddl([f"DROP TABLE {name}"]).result(600)
    except Exception:  # noqa: BLE001
        pass
    return ok({"txn": out.get("txn"), "ddl": out.get("ddl"), "txn_retried": rec["calls"] > 1})


# ---------- 制限・API ----------
def A4(db, ctx):
    def f():
        with db.snapshot() as s:
            n = list(s.execute_sql("SELECT COUNT(*) FROM Item a, Item b, Item c WHERE a.price + b.price + c.price > 0", timeout=0.001, retry=None))[0][0]
        return ok({"count": n})
    return run(f)


def A5(db, ctx):
    def f():
        with db.snapshot() as s:
            rs = s.execute_sql("SELECT id FROM Item@{FORCE_INDEX=ItemByCat} WHERE cat = 'c1'", query_mode=1)  # PLAN
            list(rs)
            plan = rs.stats.query_plan if rs.stats else None
            nodes = list(plan.plan_nodes) if plan else []
            text = " ".join(str(n) for n in nodes)
        return ok({"has_plan_nodes": len(nodes) > 0, "mentions_index": "ItemByCat" in text})
    return run(f)


def A6(db, ctx):
    return run(lambda: (db.update_ddl(["ANALYZE"]).result(600), ok())[1])


def A7(db, ctx):
    return run(lambda: ok({"rows": db.execute_partitioned_dml(f"INSERT INTO Acc (id, v) VALUES ({1000 + ctx['rep']}, 1)")}))


def A8(db, ctx):
    def f():
        snap = db.batch_snapshot()
        try:
            batches = list(snap.generate_query_batches("SELECT id FROM Item ORDER BY id"))
            n = sum(len(list(snap.process_query_batch(b))) for b in batches)
        finally:
            snap.close()
        return ok({"rows": n})
    return run(f)


def A9(db, ctx):
    """11列×8,000行=88,000 ミューテーション(上限 80,000)を1コミットで。"""
    rows = [[i] + [f"x{i % 1000}"] * 10 for i in range(8000)]
    cols = ["id"] + [f"c{k}" for k in range(1, 11)]
    def f():
        db.run_in_transaction(lambda tx: tx.insert("Big", cols, rows))
        return ok({"inserted": True})
    r = run(f)
    try:
        db.execute_partitioned_dml("DELETE FROM Big WHERE true")
    except Exception:  # noqa: BLE001
        pass
    return r


def A10(db, ctx):
    """1コミットに主キー重複と外部キー違反を同時に入れる。"""
    def f():
        def fn(tx):
            tx.insert("Parent", ["id"], [[1]])          # 重複(seed で 1 は存在)
            tx.insert("Child", ["id", "pid"], [[1, 999]])  # 外部キー違反
        db.run_in_transaction(fn)
        return ok()
    r = run(f)
    m = r["message"]
    r["value"] = {"reports": "already_exists" if ("already exists" in m.lower() or "ALREADY_EXISTS" in r["status"]) else
                  ("foreign_key" if "foreign key" in m.lower() else ("ok" if r["status"] == "OK" else "other"))}
    return r


def A11(db, ctx):
    out = {}
    for name, sql in [("ST_GEOGPOINT", "SELECT ST_GEOGPOINT(1.0, 2.0)"), ("APPROX_QUANTILES", "SELECT APPROX_QUANTILES(x, 2) FROM UNNEST([1, 2, 3]) AS x"),
                      ("PARSE_BIGNUMERIC", "SELECT PARSE_BIGNUMERIC('1.5')")]:
        def f(sql=sql):
            with db.snapshot() as s:
                list(s.execute_sql(sql))
            return ok()
        out[name] = run(f)["status"]
    return ok(out)


def A12(db, ctx):
    def f():
        with db.snapshot() as s:
            list(s.execute_sql("SELECT * FROM SPANNER_SYS.QUERY_STATS_TOP_MINUTE LIMIT 1"))
        return ok()
    return run(f)


def A14(db, ctx):
    """drop protection を付けた別 DB を削除しようとする。"""
    from targets import instance
    inst = instance(ctx["target"]); name = "dropprot"
    d = inst.database(name)
    if not d.exists():
        d.create().result(600)
    d.update_ddl([f"ALTER DATABASE `{name}` SET OPTIONS (enable_drop_protection = true)"]).result(600)
    r = run(lambda: (d.drop(), ok())[1])
    exists_after = d.exists()
    if exists_after:
        d.update_ddl([f"ALTER DATABASE `{name}` SET OPTIONS (enable_drop_protection = false)"]).result(600)
        d.drop()
    r["value"] = {"exists_after_drop": exists_after}
    return r


def A15(db, ctx):
    out = {}
    for name, sql in [("plain", "SELECT id FROM Doc WHERE SEARCH(tok, 'database') ORDER BY id"),
                      ("enhance_query", "SELECT id FROM Doc WHERE SEARCH(tok, 'database', enhance_query => true) ORDER BY id"),
                      ("language_tag_ja", "SELECT id FROM Doc WHERE SEARCH(tok_ja, 'データベース') ORDER BY id")]:
        def f(sql=sql):
            with db.snapshot() as s:
                return ok([r[0] for r in s.execute_sql(sql)])
        r = run(f); out[name] = [r["status"], r["value"]]
    return ok(out)


def A16(db, ctx):
    from targets import client
    def f():
        return ok({"n": len(list(client(ctx["target"]).list_instances(filter_="labels.omnitest:nomatch")))})
    return run(f)


def B1(db, ctx):
    out = {}
    for p in ["8d", "30d"]:
        r = run(lambda p=p: (db.update_ddl([f"ALTER DATABASE `{db.database_id}` SET OPTIONS (version_retention_period = '{p}')"]).result(600), ok())[1])
        out[p] = r["status"]
    run(lambda: (db.update_ddl([f"ALTER DATABASE `{db.database_id}` SET OPTIONS (version_retention_period = '1h')"]).result(600), ok())[1])
    return ok(out)


def B2(db, ctx):
    name = f"M{ctx['rep']}"
    r = run(lambda: (db.update_ddl([f"CREATE MODEL {name} INPUT (x STRING(MAX)) OUTPUT (y STRING(MAX)) REMOTE OPTIONS "
                                    f"(endpoint = '//aiplatform.googleapis.com/projects/PROJECT_ID/locations/asia-northeast1/endpoints/1')"]).result(600), ok())[1])
    run(lambda: (db.update_ddl([f"DROP MODEL {name}"]).result(600), ok())[1])
    return r


def B3(db, ctx):
    def f():
        snap = db.batch_snapshot()
        try:
            batches = list(snap.generate_query_batches("SELECT id FROM Item", data_boost_enabled=True))
            n = sum(len(list(snap.process_query_batch(b))) for b in batches)
        finally:
            snap.close()
        return ok({"rows": n})
    return run(f)


# ---------- 対照 ----------
def C1(db, ctx):
    def f():
        with db.snapshot() as s:
            return ok([list(r) for r in s.execute_sql("SELECT id, cat, price FROM Item WHERE id IN (3, 150) ORDER BY id")])
    return run(f)


def C2(db, ctx):
    return run(lambda: (db.run_in_transaction(lambda tx: tx.insert("Child", ["id", "pid"], [[10, 999]])), ok())[1])


def C3(db, ctx):
    r = run(lambda: (db.run_in_transaction(lambda tx: tx.insert("Chk", ["id", "x"], [[ctx["rep"], -1]])), ok())[1])
    return r


def C4(db, ctx):
    def f():
        reset(db, ["Ts"])
        ts = db.run_in_transaction(lambda tx: tx.insert("Ts", ["id", "t"], [[1, "spanner.commit_timestamp()"]]))
        with db.snapshot() as s:
            t = list(s.execute_sql("SELECT t FROM Ts WHERE id=1"))[0][0]
        commit_ts = getattr(db, "_last_commit_ts", None)
        return ok({"has_value": t is not None})
    return run(f)


def C5(db, ctx):
    def f():
        reset(db, ["Gen"]); db.run_in_transaction(lambda tx: tx.insert("Gen", ["id", "a"], [[1, 21]]))
        with db.snapshot() as s:
            return ok(list(s.execute_sql("SELECT b FROM Gen WHERE id=1"))[0][0])
    return run(f)


def C6(db, ctx):
    def f():
        from google.cloud.spanner_v1 import JsonObject
        reset(db, ["Typ"])
        db.run_in_transaction(lambda tx: tx.insert("Typ", ["id", "j", "n"], [[1, JsonObject({"a": [1, 2], "b": "x"}), decimal.Decimal("12345.6789")]]))
        with db.snapshot() as s:
            j, n = list(s.execute_sql("SELECT j, n FROM Typ WHERE id=1"))[0]
        return ok({"j": json.loads(j.serialize()) if hasattr(j, "serialize") else j, "n": str(n)})
    return run(f)


def C7(db, ctx):
    def f():
        reset(db, ["Stale"]); time.sleep(1.5)
        t0 = datetime.datetime.now(datetime.timezone.utc)
        time.sleep(1.5)
        db.run_in_transaction(lambda tx: tx.insert("Stale", ["id"], [[1]]))
        with db.snapshot(read_timestamp=t0) as s:
            before = len(list(s.execute_sql("SELECT id FROM Stale")))
        with db.snapshot() as s:
            now = len(list(s.execute_sql("SELECT id FROM Stale")))
        return ok({"before": before, "now": now})
    return run(f)


def C8(db, ctx):
    def f():
        with db.snapshot() as s:
            names = sorted(r[0] for r in s.execute_sql("SELECT table_name FROM INFORMATION_SCHEMA.TABLES WHERE table_schema = '' AND table_type = 'BASE TABLE'"))
        return ok([n for n in names if not n.startswith("DdlT")])
    return run(f)


def C9(db, ctx):
    def f():
        reset(db, ["SeqT"])
        db.run_in_transaction(lambda tx: [tx.execute_update(f"INSERT INTO SeqT (x) VALUES ({i})") for i in range(5)])
        with db.snapshot() as s:
            ids = [r[0] for r in s.execute_sql("SELECT id FROM SeqT")]
        return ok({"n": len(ids), "unique": len(set(ids)) == len(ids), "positive": all(i > 0 for i in ids)})
    return run(f)


def C10(db, ctx):
    def f():
        with db.snapshot() as s:
            return ok(sorted(tuple(r) for r in s.execute_sql("GRAPH G MATCH (a:Person)-[:Knows]->(b:Person) RETURN a.name AS a, b.name AS b")))
    return run(f)


def C11(db, ctx):
    return run(lambda: (db.run_in_transaction(lambda tx: tx.insert("Parent", ["id"], [[1]])), ok())[1])


def C12(db, ctx):
    def f():
        with db.snapshot() as s:
            list(s.execute_sql("SELECT * FROM NoSuchTable"))
        return ok()
    return run(f)


CASES = {k: v for k, v in globals().items() if k[:1] in "ABC" and k[1:].isdigit()}

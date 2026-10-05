"""事前登録 v2 のテスト。各関数は (db, ctx) を受け取り {"status", "value", "message"} を返す。
status は "OK" か gRPC のステータスコード名。value は Cloud と比べる正規化した結果(行は必ずソート)。
性能は測らない(ライセンス 3.4。所要時間は記録しない)。"""
import threading, time, json, decimal, os, subprocess
from google.api_core import exceptions as gex  # noqa: F401
from google.cloud.spanner_v1 import param_types, TransactionOptions

SER = dict(isolation_level=TransactionOptions.IsolationLevel.SERIALIZABLE,
           read_lock_mode=TransactionOptions.ReadWrite.ReadLockMode.PESSIMISTIC)

SCHEMA = [
    "CREATE TABLE Acc (id INT64 NOT NULL, v INT64) PRIMARY KEY (id)",
    "CREATE TABLE Big8 (id INT64 NOT NULL, c1 STRING(10), c2 STRING(10), c3 STRING(10), c4 STRING(10), c5 STRING(10), c6 STRING(10), c7 STRING(10)) PRIMARY KEY (id)",
    "CREATE TABLE One (id INT64 NOT NULL) PRIMARY KEY (id)",
    "CREATE TABLE Blob (id INT64 NOT NULL, b BYTES(MAX)) PRIMARY KEY (id)",
    "CREATE TABLE Parent (id INT64 NOT NULL) PRIMARY KEY (id)",
    "CREATE TABLE Child (id INT64 NOT NULL, pid INT64, CONSTRAINT FK_Child_Parent FOREIGN KEY (pid) REFERENCES Parent (id)) PRIMARY KEY (id)",
    "CREATE TABLE Chk (id INT64 NOT NULL, x INT64, CONSTRAINT x_pos CHECK (x > 0)) PRIMARY KEY (id)",
    "CREATE TABLE Ts (id INT64 NOT NULL, t TIMESTAMP OPTIONS (allow_commit_timestamp = true)) PRIMARY KEY (id)",
    "CREATE TABLE Gen (id INT64 NOT NULL, a INT64, b INT64 AS (a * 2) STORED) PRIMARY KEY (id)",
    "CREATE TABLE Typ (id INT64 NOT NULL, j JSON, n NUMERIC) PRIMARY KEY (id)",
    "CREATE TABLE Stale (id INT64 NOT NULL) PRIMARY KEY (id)",
    "CREATE SEQUENCE Sq OPTIONS (sequence_kind = 'bit_reversed_positive')",
    "CREATE TABLE SeqT (id INT64 NOT NULL DEFAULT (GET_NEXT_SEQUENCE_VALUE(SEQUENCE Sq)), x INT64) PRIMARY KEY (id)",
    "CREATE TABLE UuidT (id STRING(36) NOT NULL DEFAULT (GENERATE_UUID()), x INT64) PRIMARY KEY (id)",
    "CREATE TABLE Person (id INT64 NOT NULL, name STRING(20)) PRIMARY KEY (id)",
    "CREATE TABLE Knows (id INT64 NOT NULL, dst INT64 NOT NULL) PRIMARY KEY (id, dst)",
    "CREATE PROPERTY GRAPH G NODE TABLES (Person) EDGE TABLES (Knows SOURCE KEY (id) REFERENCES Person (id) DESTINATION KEY (dst) REFERENCES Person (id) LABEL Knows)",
    "CREATE TABLE Doc (id INT64 NOT NULL, body STRING(MAX), tok TOKENLIST AS (TOKENIZE_FULLTEXT(body)) HIDDEN) PRIMARY KEY (id)",
    "CREATE SEARCH INDEX DocIdx ON Doc (tok)",
    "CREATE TABLE Dia (id INT64 NOT NULL, body STRING(MAX), sub_rd TOKENLIST AS (TOKENIZE_SUBSTRING(body, remove_diacritics => true)) HIDDEN, "
    "sub_plain TOKENLIST AS (TOKENIZE_SUBSTRING(body)) HIDDEN) PRIMARY KEY (id)",
    "CREATE SEARCH INDEX DiaIdx ON Dia (sub_rd, sub_plain)",
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


def q(db, sql, **kw):
    with db.snapshot() as s:
        return [list(r) for r in s.execute_sql(sql, **kw)]


def sub(fn):
    """副テスト1件の [status, value, message]。message は拒否の理由の分類に使う(比較対象外)。"""
    r = run(fn)
    return [r["status"], r["value"], (r.get("message") or "")[:160]]


def ddl(db, stmts):
    db.update_ddl(stmts).result(900)


def reset(db, tables):
    def fn(tx):
        for t in tables:
            tx.execute_update(f"DELETE FROM {t} WHERE true")
    db.run_in_transaction(fn)


def seed(db):
    reset(db, ["Child", "Parent", "Item", "Person", "Knows", "Doc", "Acc"])
    def fn(tx):
        tx.insert("Parent", ["id"], [[1], [2]])
        tx.insert("Child", ["id", "pid"], [[1, 1]])
        tx.insert("Item", ["id", "cat", "price"], [[i, f"c{i % 10}", (i * 37) % 300] for i in range(300)])
        tx.insert("Person", ["id", "name"], [[1, "alice"], [2, "bob"], [3, "carol"]])
        tx.insert("Knows", ["id", "dst"], [[1, 2], [2, 3]])
        tx.insert("Doc", ["id", "body"], [[1, "Spanner database engine"], [2, "分散データベースのエンジン"], [3, "running databases"]])
        tx.insert_or_update("Dia", ["id", "body"], [[1, "café au lait"]])
    db.run_in_transaction(fn)


# ---------- 並行性(SERIALIZABLE・PESSIMISTIC を明示、Barrier で重なりを確認) ----------
def _pair(db, body, keys, barrier_timeout=5.0):
    """2本の読み書きトランザクション。各試行で「どこまで進んだか」を記録し、次の試行が始まったら前の試行の中断位置とみなす。"""
    bar = threading.Barrier(2, timeout=barrier_timeout)
    rec = {n: {"attempts": []} for n in "AB"}; errs = {}
    def go(name, key):
        def fn(tx):
            steps = []; rec[name]["attempts"].append(steps)
            body(tx, key, steps, bar if len(rec[name]["attempts"]) == 1 else None)
            steps.append("buffered")
        try:
            db.run_in_transaction(fn, **SER)
        except Exception as e:  # noqa: BLE001
            errs[name] = err(e)["status"]
    ts = [threading.Thread(target=go, args=(n, k)) for n, k in zip("AB", keys)]
    [t.start() for t in ts]; [t.join() for t in ts]
    aborted_at = []
    for n in "AB":
        for st in rec[n]["attempts"][:-1]:
            aborted_at.append("at_read_rpc" if "read" not in st else ("at_commit_rpc" if "buffered" in st else "after_read"))
    overlap = all(any("barrier_passed" in st for st in rec[n]["attempts"][:1]) for n in "AB")
    return {"overlap": overlap, "aborted_at": sorted(aborted_at), "attempts": [len(rec["A"]["attempts"]), len(rec["B"]["attempts"])], "errs": errs}


def _rmw(tx, key, steps, bar):
    v = list(tx.execute_sql("SELECT v FROM Acc WHERE id=@k", params={"k": key}, param_types={"k": param_types.INT64}))[0][0]
    steps.append("read"); steps.append(f"v={v}")
    if bar is not None:
        try:
            bar.wait(); steps.append("barrier_passed")
        except threading.BrokenBarrierError:
            steps.append("barrier_broken")
    tx.update("Acc", ["id", "v"], [[key, v + 1]])


def A1(db, ctx):
    """別々の行。性質: 両方コミット、最終値 (1,1),(2,1)。観測: 中断の有無と位置、重なり。"""
    reset(db, ["Acc"]); db.run_in_transaction(lambda tx: tx.insert("Acc", ["id", "v"], [[1, 0], [2, 0]]))
    r = _pair(db, _rmw, (1, 2))
    final = sorted(tuple(x) for x in q(db, "SELECT id, v FROM Acc"))
    return ok({**r, "final_ok": final == [(1, 1), (2, 1)]})


def A2(db, ctx):
    """同じ行。性質: 最終値=2(更新の消失なし)。観測: 両方が初期値を読んで重なったか、中断の位置。"""
    reset(db, ["Acc"]); db.run_in_transaction(lambda tx: tx.insert("Acc", ["id", "v"], [[1, 0]]))
    r = _pair(db, _rmw, (1, 1))
    final = q(db, "SELECT v FROM Acc WHERE id=1")[0][0]
    return ok({**r, "final_ok": final == 2})


def A3(db, ctx):
    """読み書きトランザクション(0.5秒ごとに読み続けて約3秒)の最中に、別テーブルの DDL を出す。"""
    reset(db, ["Acc"]); db.run_in_transaction(lambda tx: tx.insert("Acc", ["id", "v"], [[1, 0]]))
    rec = {"attempts": 0, "seq": []}; out = {}; first_read = threading.Event()
    def fn(tx):
        rec["attempts"] += 1
        for i in range(6):
            list(tx.execute_sql("SELECT v FROM Acc WHERE id=1"))
            if i == 0:
                rec["seq"].append("txn_read1"); first_read.set()
            time.sleep(0.5)
        tx.update("Acc", ["id", "v"], [[1, 1]])
    def txn():
        try:
            db.run_in_transaction(fn, **SER); out["txn"] = "OK"
        except Exception as e:  # noqa: BLE001
            out["txn"] = err(e)["status"]
    t = threading.Thread(target=txn); t.start()
    started = first_read.wait(30)                  # トランザクションが最初の読み取りを終えてから DDL を出す(時間ではなく順序で制御)
    name = f"DdlT{ctx['run']}_{ctx['rep']}"
    rec["seq"].append("ddl_start")
    d = sub(lambda: (ddl(db, [f"CREATE TABLE {name} (id INT64 NOT NULL) PRIMARY KEY (id)"]), ok())[1]); out["ddl"] = d[0]; out["ddl_msg"] = d[2]
    rec["seq"].append("ddl_end")
    t.join(); rec["seq"].append("txn_end")
    run(lambda: (ddl(db, [f"DROP TABLE {name}"]), ok())[1])
    return ok({"txn": out.get("txn"), "ddl": out["ddl"], "ddl_msg": out["ddl_msg"], "txn_retried": rec["attempts"] > 1, "ddl_after_txn_read": started, "seq": rec["seq"]})


# ---------- 計画・統計 ----------
def A5(db, ctx):
    """PLAN モード(陽性対照)。FORCE_INDEX を付け、計画のノードが返るか。"""
    def f():
        with db.snapshot() as s:
            rs = s.execute_sql("SELECT id FROM Item@{FORCE_INDEX=ItemByCat} WHERE cat = 'c1'", query_mode=1); list(rs)
            nodes = list(rs.stats.query_plan.plan_nodes) if rs.stats and rs.stats.query_plan else []
        return ok({"has_plan_nodes": len(nodes) > 0})
    return run(f)


def A5b(db, ctx):
    """PROFILE モード。計画のノードと、行数の統計が返るか(実行時間は記録しない)。"""
    def f():
        with db.snapshot() as s:
            rs = s.execute_sql("SELECT id FROM Item@{FORCE_INDEX=ItemByCat} WHERE cat = 'c1'", query_mode=2); rows = list(rs)
            nodes = list(rs.stats.query_plan.plan_nodes) if rs.stats and rs.stats.query_plan else []
            qs = dict(rs.stats.query_stats) if rs.stats and rs.stats.query_stats else {}
        return ok({"has_plan_nodes": len(nodes) > 0, "rows_returned_stat": qs.get("rows_returned"), "rows": len(rows)})
    return run(f)


def A6(db, ctx):
    """ANALYZE の前後で統計パッケージの数が増えるか。"""
    def cnt():
        return q(db, "SELECT COUNT(*) FROM INFORMATION_SCHEMA.SPANNER_STATISTICS")[0][0]
    before = sub(lambda: ok(cnt()))
    st = sub(lambda: (ddl(db, ["ANALYZE"]), ok())[1])
    after = sub(lambda: ok(cnt()))
    inc = (before[0] == "OK" and after[0] == "OK" and after[1] > before[1])
    return ok({"stats_query": before[0], "analyze": st[0], "package_increased": inc})


# ---------- Partitioned DML / partitionQuery ----------
def A7(db, ctx):
    out = {}
    out["insert"] = sub(lambda: ok(db.execute_partitioned_dml(f"INSERT INTO Acc (id, v) VALUES ({1000 + ctx['rep']}, 1)") >= 0))
    out["delete_not_in_subquery"] = sub(lambda: ok(db.execute_partitioned_dml("DELETE FROM Child WHERE pid NOT IN (SELECT id FROM Parent)") >= 0))
    out["update_self_read"] = sub(lambda: ok(db.execute_partitioned_dml("UPDATE Acc SET v = (SELECT MAX(v) FROM Acc) WHERE true") >= 0))
    return ok(out)


def _pq(db, sql, **kw):
    snap = db.batch_snapshot()
    try:
        batches = list(snap.generate_query_batches(sql, **kw))
        return ok(sorted(r[0] for b in batches for r in snap.process_query_batch(b))[:3])
    finally:
        snap.close()


def A8(db, ctx):
    return ok({"order_by_nonkey": sub(lambda: _pq(db, "SELECT id FROM Item ORDER BY price")),
               "count_star": sub(lambda: _pq(db, "SELECT COUNT(*) FROM Item"))})


# ---------- 上限 ----------
def A9(db, ctx):
    """ミューテーション数の境界(列数×行数。Big8 は8列、索引なし)と、1セルのサイズの境界(10MiB)。"""
    cols = ["id"] + [f"c{k}" for k in range(1, 8)]
    def m(n_rows, extra):
        def f():
            def fn(tx):
                tx.insert("Big8", cols, [[i] + ["x"] * 7 for i in range(n_rows)])
                if extra:
                    tx.insert("One", ["id"], [[ctx["rep"] * 10 + 1]])
            db.run_in_transaction(fn)
            return ok()
        r = sub(f)
        for t in ("Big8", "One"):
            run(lambda t=t: ok(db.execute_partitioned_dml(f"DELETE FROM {t} WHERE true")))
        return r
    def cell(nbytes):
        def f():
            import base64   # 3.71.0 は bytes を base64 済みとして送るので、実際の大きさ nbytes の値を base64 にして渡す(監査で判明、3者共通の誤りの修正)
            db.run_in_transaction(lambda tx: tx.insert_or_update("Blob", ["id", "b"], [[1, base64.b64encode(b"\0" * nbytes)]]))
            return ok()
        r = sub(f); run(lambda: ok(db.execute_partitioned_dml("DELETE FROM Blob WHERE true")))
        return r
    return ok({"mut_80000": m(10000, False), "mut_80001": m(10000, True), "mut_160000": m(20000, False),
               "cell_10MiB": cell(10 * 1024 * 1024), "cell_10MiB_plus1": cell(10 * 1024 * 1024 + 1)})


def A10(db, ctx):
    """1コミットに主キー重複と外部キー違反。ミューテーションの順序を2通り。"""
    def classify(r):
        msg = (r["message"] or "").lower()
        return "already_exists" if (r["status"] == "ALREADY_EXISTS" or "already exists" in msg) else ("foreign_key" if "foreign key" in msg else r["status"])
    def order(dup_first):
        def f():
            def fn(tx):
                if dup_first:
                    tx.insert("Parent", ["id"], [[1]]); tx.insert("Child", ["id", "pid"], [[50, 999]])
                else:
                    tx.insert("Child", ["id", "pid"], [[50, 999]]); tx.insert("Parent", ["id"], [[1]])
            db.run_in_transaction(fn); return ok()
        r = run(f); return [r["status"], classify(r), (r["message"] or "")[:160]]
    return ok({"dup_first": order(True), "fk_first": order(False)})


FN20 = {  # sources/fn_sample20.txt(シード 20261005 で抽出)ごとの最小の呼び出し
    "APPROX_COUNT_DISTINCT": "SELECT APPROX_COUNT_DISTINCT(x) FROM UNNEST([1, 2, 2]) AS x",
    "COTH": "SELECT COTH(1.0)",
    "COVAR_POP": "SELECT COVAR_POP(x, y) FROM UNNEST([STRUCT(1.0 AS x, 2.0 AS y), STRUCT(2.0, 3.0)])",
    "CUME_DIST": "SELECT CUME_DIST() OVER (ORDER BY x) FROM UNNEST([1, 2]) AS x",
    "DETERMINISTIC_DECRYPT_BYTES": "SELECT DETERMINISTIC_DECRYPT_BYTES(b'k', b'c', 'a')",
    "IS_LAST": "SELECT IS_LAST(1) OVER (ORDER BY x) FROM UNNEST([1, 2]) AS x",
    "JSON_EXTRACT_ARRAY": "SELECT JSON_EXTRACT_ARRAY(JSON '[1, 2]')",
    "JSON_EXTRACT_SCALAR": "SELECT JSON_EXTRACT_SCALAR('{\"a\": 1}', '$.a')",
    "JSON_FLATTEN": "SELECT JSON_FLATTEN(JSON '[[1], [2]]')",
    "MAP_CARDINALITY": "SELECT MAP_CARDINALITY(MAP_FROM_ARRAY([('a', 1)]))",
    "MAP_EMPTY": "SELECT MAP_EMPTY(MAP_FROM_ARRAY([('a', 1)]))",
    "MAP_KEYS_SORTED": "SELECT MAP_KEYS_SORTED(MAP_FROM_ARRAY([('a', 1)]))",
    "PERCENTILE_CONT": "SELECT PERCENTILE_CONT(x, 0.5) OVER () FROM UNNEST([1.0, 2.0]) AS x",
    "PI_BIGNUMERIC": "SELECT PI_BIGNUMERIC()",
    "PROTO_DEFAULT_IF_NULL": "SELECT PROTO_DEFAULT_IF_NULL(NULL)",
    "PROTO_MODIFY_MAP": "SELECT PROTO_MODIFY_MAP(NULL, 'a', 1)",
    "ST_ASBINARY": "SELECT ST_ASBINARY(ST_GEOGPOINT(1, 2))",
    "ST_DISTANCE": "SELECT ST_DISTANCE(ST_GEOGPOINT(1, 2), ST_GEOGPOINT(1, 3))",
    "ST_EQUALS": "SELECT ST_EQUALS(ST_GEOGPOINT(1, 2), ST_GEOGPOINT(1, 2))",
    "ST_TOUCHES": "SELECT ST_TOUCHES(ST_GEOGPOINT(1, 2), ST_GEOGPOINT(1, 2))",
}


def A11(db, ctx):
    return ok({k: sub(lambda s=s: ok(len(q(db, s)))) for k, s in FN20.items()})


def A12(db, ctx):
    return run(lambda: ok(len(q(db, "SELECT * FROM SPANNER_SYS.QUERY_STATS_TOP_MINUTE LIMIT 1")) >= 0))


def A14(db, ctx):
    """陽性対照。削除保護を付けた別 DB(dropprot)を削除しようとする。後片付け: 保護を外して削除。"""
    from targets import instance
    inst = instance(ctx["target"]); name = "dropprot"
    d = inst.database(name)
    created = sub(lambda: ok(True if d.exists() else (d.create().result(600), True)[1]))
    if created[0] != "OK":
        return ok({"create": created[0], "create_msg": created[2]})
    lro = {}
    def protect(flag):
        def f():
            d.reload(); d.enable_drop_protection = flag; op = d.update(["enable_drop_protection"])
            lro[flag] = sub(lambda: (op.result(600), ok())[1])[0]       # 長時間オペレーションの完了確認(Omni で NOT_FOUND を観測、事後の発見)
            for _ in range(30):                                           # 設定が反映されたかは読み直して確かめる
                d.reload()
                if d.enable_drop_protection == flag:
                    return ok()
                time.sleep(2)
            return {"status": "NOT_APPLIED", "value": None, "message": ""}
        return f
    set_st = sub(protect(True))[0]
    drop_st = sub(lambda: (d.drop(), ok())[1])[0]
    exists_after = sub(lambda: ok(d.exists()))[1]
    if exists_after:
        run(protect(False)); run(lambda: (d.drop(), ok())[1])
    return ok({"set_protection": set_st, "set_lro": lro.get(True), "drop": drop_st, "exists_after_drop": exists_after})  # set_lro は比較対象外(事後の発見の記録)


def A15(db, ctx):
    """全文検索の引数(エミュレータ README の小項目)。引数あり/なしを対にし、「引数で出力が変わったか」を見る。
    エミュレータが DEBUG_TOKENLIST を受け付けない場合に備え、remove_diacritics は SEARCH_SUBSTRING の結果でも比べる。"""
    def pair(with_arg, without_arg):
        a = sub(lambda: ok(q(db, with_arg)[0][0])); b = sub(lambda: ok(q(db, without_arg)[0][0]))
        changed = (a[1] != b[1]) if (a[0] == "OK" and b[0] == "OK") else None
        return {"with": a[0], "without": b[0], "changed": changed, "with_value": a[1], "msg": a[2] or b[2]}
    D = lambda s: f"SELECT DEBUG_TOKENLIST({s})"
    out = {
        "language_tag_ja": pair(D("TOKENIZE_FULLTEXT('分散データベースのエンジン', language_tag => 'ja')"), D("TOKENIZE_FULLTEXT('分散データベースのエンジン')")),
        "content_type_html": pair(D("TOKENIZE_FULLTEXT('<b>bold</b> text', content_type => 'text/html')"), D("TOKENIZE_FULLTEXT('<b>bold</b> text')")),
        "token_category_title": pair(D("TOKENIZE_FULLTEXT('Hello world', token_category => 'title')"), D("TOKENIZE_FULLTEXT('Hello world')")),
        "substring_remove_diacritics": pair(D("TOKENIZE_SUBSTRING('café', remove_diacritics => true)"), D("TOKENIZE_SUBSTRING('café')")),
        "substring_short_tokens_only_for_anchors": pair(D("TOKENIZE_SUBSTRING('ab cdef', short_tokens_only_for_anchors => true)"), D("TOKENIZE_SUBSTRING('ab cdef')")),
        "ngrams_remove_diacritics": pair(D("TOKENIZE_NGRAMS('café', remove_diacritics => true)"), D("TOKENIZE_NGRAMS('café')")),
        "search_remove_diacritics": {"rd_index": sub(lambda: ok(sorted(x[0] for x in q(db, "SELECT id FROM Dia WHERE SEARCH_SUBSTRING(sub_rd, 'cafe')")))),
                                     "plain_index": sub(lambda: ok(sorted(x[0] for x in q(db, "SELECT id FROM Dia WHERE SEARCH_SUBSTRING(sub_plain, 'cafe')"))))},
        "score_options": sub(lambda: ok([round(x[0], 6) for x in q(db, "SELECT SCORE(tok, 'database engine', options => JSON '{\"bigram_weight\": 3.0}') FROM Doc WHERE SEARCH(tok, 'database engine')")]
                                         != [round(x[0], 6) for x in q(db, "SELECT SCORE(tok, 'database engine') FROM Doc WHERE SEARCH(tok, 'database engine')")])),
        "enhance_query_on": sub(lambda: ok(sorted(x[0] for x in q(db, "SELECT id FROM Doc WHERE SEARCH(tok, 'databases', enhance_query => true)")))),
        "enhance_query_off": sub(lambda: ok(sorted(x[0] for x in q(db, "SELECT id FROM Doc WHERE SEARCH(tok, 'databases')")))),
        "search_index_options": sub(lambda: (ddl(db, [f"CREATE SEARCH INDEX DocIdxOpt{ctx['run']}_{ctx['rep']} ON Doc (tok) OPTIONS (sort_order_sharding = true)"]), ok())[1]),
    }
    run(lambda: (ddl(db, [f"DROP SEARCH INDEX DocIdxOpt{ctx['run']}_{ctx['rep']}"]), ok())[1])
    return ok(out)


def A16(db, ctx):
    """ListSessions のラベル絞り込み。ラベル付きのセッションを1つ作り、合わないラベルで絞る。"""
    def f():
        api = db.spanner_api
        s = api.create_session(request={"database": db.name, "session": {"labels": {"omnitest": f"r{ctx['rep']}"}}})   # 多重化しない通常のセッション
        try:
            match = [x.name for x in api.list_sessions(request={"database": db.name, "filter": f"labels.omnitest:r{ctx['rep']}"})]
            nomatch = [x.name for x in api.list_sessions(request={"database": db.name, "filter": "labels.omnitest:nomatch"})]
            return ok({"match_contains": s.name in match, "nomatch_contains": s.name in nomatch})
        finally:
            api.delete_session(request={"name": s.name})
    return run(f)


def A17(db, ctx):
    """外部キーの裏の索引名を INFORMATION_SCHEMA から取り、FORCE_INDEX に使う。"""
    def f():
        names = [r[0] for r in q(db, "SELECT index_name FROM INFORMATION_SCHEMA.INDEXES WHERE table_name = 'Child' AND index_type = 'INDEX' AND spanner_is_managed")]
        if not names:
            return ok({"backing_index_found": False})
        st = sub(lambda: ok(len(q(db, f"SELECT id FROM Child@{{FORCE_INDEX={names[0]}}} WHERE pid = 1"))))
        return ok({"backing_index_found": True, "force_index": st[0]})
    return run(f)


# ---------- Omni の非対応(S3)。正解は Cloud ではなく S3 の記述。Cloud で成功しなければ無効 ----------
def B1(db, ctx):
    """予備の DB(cmpb1)で流す(保持期間を延ばすとスキーマの版が長く残るため本体の DB を避ける)。"""
    from targets import database
    db = database(ctx["target"], "cmpb1")
    out = {}
    for p in ["7d", "8d", "30d", "31d"]:
        out[p] = sub(lambda p=p: (ddl(db, [f"ALTER DATABASE `{db.database_id}` SET OPTIONS (version_retention_period = '{p}')"]), ok())[1])[0]
    run(lambda: (ddl(db, [f"ALTER DATABASE `{db.database_id}` SET OPTIONS (version_retention_period = '1h')"]), ok())[1])
    return ok(out)


def B2(db, ctx):
    name = f"M{ctx['run']}_{ctx['rep']}"
    r = run(lambda: (ddl(db, [f"CREATE MODEL {name} INPUT (x STRING(MAX)) OUTPUT (y STRING(MAX)) REMOTE OPTIONS "
                             f"(endpoint = '//aiplatform.googleapis.com/projects/{os.environ.get('CLOUD_PROJECT', 'PROJECT_ID')}/locations/asia-northeast1/endpoints/1')"]), ok())[1])
    run(lambda: (ddl(db, [f"DROP MODEL {name}"]), ok())[1])
    return r


def B3(db, ctx):
    return run(lambda: _pq(db, "SELECT id FROM Item", data_boost_enabled=True))


# ---------- 対照(エミュレータ README の supported 欄。除外は事前登録に理由つき) ----------
def C1(db, ctx):
    return run(lambda: ok(q(db, "SELECT id, cat, price FROM Item WHERE id IN (3, 150) ORDER BY id")))


def C2(db, ctx):
    return run(lambda: (db.run_in_transaction(lambda tx: tx.insert("Child", ["id", "pid"], [[10, 999]])), ok())[1])


def C3(db, ctx):
    return run(lambda: (db.run_in_transaction(lambda tx: tx.insert("Chk", ["id", "x"], [[ctx["rep"], -1]])), ok())[1])


def C4(db, ctx):
    def f():
        reset(db, ["Ts"])
        db.run_in_transaction(lambda tx: tx.insert("Ts", ["id", "t"], [[1, "spanner.commit_timestamp()"]]))
        return ok({"has_value": q(db, "SELECT t FROM Ts WHERE id=1")[0][0] is not None})
    return run(f)


def C5(db, ctx):
    def f():
        reset(db, ["Gen"]); db.run_in_transaction(lambda tx: tx.insert("Gen", ["id", "a"], [[1, 21]]))
        return ok(q(db, "SELECT b FROM Gen WHERE id=1")[0][0])
    return run(f)


def C6(db, ctx):
    def f():
        from google.cloud.spanner_v1 import JsonObject
        reset(db, ["Typ"])
        db.run_in_transaction(lambda tx: tx.insert("Typ", ["id", "j", "n"], [[1, JsonObject({"a": [1, 2], "b": "x"}), decimal.Decimal("12345.6789")]]))
        j, n = q(db, "SELECT j, n FROM Typ WHERE id=1")[0]
        return ok({"j": json.loads(j.serialize()) if hasattr(j, "serialize") else j, "n": str(n)})
    return run(f)


def C7(db, ctx):
    """exact staleness。書き込みのコミットタイムスタンプ −1µs で読む(クライアントの時計に依存しない)。"""
    def f():
        import datetime
        reset(db, ["Stale"])
        with db.batch() as b:
            b.insert("Stale", ["id"], [[1]])
        cts = b.committed
        with db.snapshot(read_timestamp=cts - datetime.timedelta(microseconds=1)) as s:
            before = len(list(s.execute_sql("SELECT id FROM Stale")))
        with db.snapshot(read_timestamp=cts) as s:
            at = len(list(s.execute_sql("SELECT id FROM Stale")))
        return ok({"before": before, "at": at})
    return run(f)


def C8(db, ctx):
    return run(lambda: ok(sorted(n for (n,) in q(db, "SELECT table_name FROM INFORMATION_SCHEMA.TABLES WHERE table_schema = '' AND table_type = 'BASE TABLE'") if not n.startswith("DdlT"))))


def C9(db, ctx):
    def f():
        reset(db, ["SeqT"])
        db.run_in_transaction(lambda tx: [tx.execute_update(f"INSERT INTO SeqT (x) VALUES ({i})") for i in range(5)])
        ids = [r[0] for r in q(db, "SELECT id FROM SeqT")]
        return ok({"n": len(ids), "unique": len(set(ids)) == len(ids), "positive": all(i > 0 for i in ids)})
    return run(f)


def C10(db, ctx):
    return run(lambda: ok(sorted(q(db, "GRAPH G MATCH (a:Person)-[:Knows]->(b:Person) RETURN a.name AS a, b.name AS b"))))


def C11(db, ctx):
    return run(lambda: (db.run_in_transaction(lambda tx: tx.insert("Parent", ["id"], [[1]])), ok())[1])


def C12(db, ctx):
    return run(lambda: ok(q(db, "SELECT * FROM NoSuchTable")))


def C13(db, ctx):
    """DDL のスキーマ変更(列の追加と削除)。"""
    col = f"extra{ctx['run']}_{ctx['rep']}"
    r = run(lambda: (ddl(db, [f"ALTER TABLE Item ADD COLUMN {col} STRING(10)"]), ok())[1])
    run(lambda: (ddl(db, [f"ALTER TABLE Item DROP COLUMN {col}"]), ok())[1])
    return r


def C14(db, ctx):
    """DML の UPDATE が返す件数。"""
    return run(lambda: ok(db.run_in_transaction(lambda tx: tx.execute_update("UPDATE Item SET price = price WHERE cat = 'c1'"))))


def C15(db, ctx):
    """SQL を使わない読み取り(主キーの範囲)。"""
    from google.cloud.spanner_v1 import KeySet, KeyRange
    def f():
        with db.snapshot() as s:
            return ok(sorted(r[0] for r in s.read("Item", ["id"], KeySet(ranges=[KeyRange(start_closed=[10], end_open=[15])]))))
    return run(f)


def C16(db, ctx):
    """二次索引を使った読み取り。"""
    from google.cloud.spanner_v1 import KeySet
    def f():
        with db.snapshot() as s:
            return ok(sorted(r[0] for r in s.read("Item", ["id"], KeySet(keys=[["c3"]]), index="ItemByCat")))
    return run(f)


def C17(db, ctx):
    """Partitioned Read。全件数。"""
    from google.cloud.spanner_v1 import KeySet
    def f():
        snap = db.batch_snapshot()
        try:
            return ok(sum(len(list(snap.process_read_batch(b))) for b in snap.generate_read_batches("Item", ["id"], KeySet(all_=True))))
        finally:
            snap.close()
    return run(f)


def C18(db, ctx):
    """分割できる Partitioned DML。"""
    return run(lambda: ok(db.execute_partitioned_dml("UPDATE Item SET price = price WHERE cat = 'c2'") >= 0))


def C19(db, ctx):
    """GENERATE_UUID による主キーの自動生成。"""
    def f():
        reset(db, ["UuidT"])
        db.run_in_transaction(lambda tx: [tx.execute_update(f"INSERT INTO UuidT (x) VALUES ({i})") for i in range(3)])
        ids = [r[0] for r in q(db, "SELECT id FROM UuidT")]
        return ok({"n": len(ids), "unique": len(set(ids)) == 3, "len36": all(len(i) == 36 for i in ids)})
    return run(f)


def C20(db, ctx):
    """PostgreSQL 方言の DB で、作成・挿入・検索。"""
    from targets import instance
    from google.cloud.spanner_admin_database_v1 import DatabaseDialect
    def f():
        inst = instance(ctx["target"])
        d = inst.database("cmppg", database_dialect=DatabaseDialect.POSTGRESQL)
        if not d.exists():
            d.create().result(600)
            d.update_ddl(["CREATE TABLE t (id bigint primary key, s varchar)"]).result(600)
        d.run_in_transaction(lambda tx: tx.execute_update("DELETE FROM t WHERE true"))
        d.run_in_transaction(lambda tx: tx.execute_update("INSERT INTO t (id, s) VALUES (1, 'a'), (2, 'b')"))
        with d.snapshot() as s:
            return ok(sorted([list(r) for r in s.execute_sql("SELECT id, s FROM t WHERE id >= $1", params={"p1": 1}, param_types={"p1": param_types.INT64})]))
    return run(f)


CASES = {k: v for k, v in globals().items() if k[:1] in "ABC" and k[1:].rstrip("b").isdigit()}
ORDER = sorted(CASES, key=lambda n: (n[0], int(n[1:].rstrip("b")), n))
CONCURRENCY = {"A1", "A2", "A3"}

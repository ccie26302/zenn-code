#!/usr/bin/env python3
"""E6 の正解: 植えたリソース(名前の規則で見つける)に、旧ロールと新ロールの SA で実際に操作し、結果の違いを記録する。
植えた設定のファイルは読まない。各操作 3 回。結果が割れたものは unstable として記録する。
出力: data/e6_truth.jsonl"""
import json, re, sys, uuid
sys.path.insert(0, __import__("os").path.dirname(__file__))
from brlib import P, ROOT, call, classify, token, user_token

S = "https://storage.googleapis.com/storage/v1"; U = "https://storage.googleapis.com/upload/storage/v1"
BQ = f"https://bigquery.googleapis.com/bigquery/v2/projects/{P}"
QP = {"x-goog-user-project": P}
PAIRS = [("owner", "admin"), ("editor", "writer"), ("viewer", "reader")]
TAG = sys.argv[1] if len(sys.argv) > 1 else "b"
out = open(ROOT / "data" / ("e6_truth.jsonl" if TAG == "b" else f"e6_truth_{TAG}.jsonl"), "w")

def res(principal, fn):
    r = [fn(token(principal)) for _ in range(3)]
    s = set(r)
    return r[0] if len(s) == 1 else "unstable"

def gcs_get(b, o):
    return lambda t: classify(*call("GET", f"{S}/b/{b}/o/{o}?alt=media", t)[:2])
def gcs_list(b):
    return lambda t: classify(*call("GET", f"{S}/b/{b}/o", t)[:2])
def gcs_create(b):
    def f(t):
        u = uuid.uuid4().hex[:8]
        st, body, _ = call("POST", f"{U}/b/{b}/o?uploadType=media&name=t-{u}.txt", t, raw=b"t")
        if 200 <= st < 300:
            call("DELETE", f"{S}/b/{b}/o/t-{u}.txt", user_token(), headers=QP)
        return classify(st, body)
    return f
def bq_read(d):
    return lambda t: classify(*call("GET", f"{BQ}/datasets/{d}/tables/t1/data?maxResults=1", t)[:2])
def bq_insert(d):
    return lambda t: classify(*call("POST", f"{BQ}/datasets/{d}/tables/t1/insertAll", t, {"rows": [{"json": {"id": 9}}]})[:2])
def bq_create(d):
    def f(t):
        u = uuid.uuid4().hex[:8]
        st, body, _ = call("POST", f"{BQ}/datasets/{d}/tables", t, {"tableReference": {"projectId": P, "datasetId": d, "tableId": f"x_{u}"}})
        if 200 <= st < 300:
            call("DELETE", f"{BQ}/datasets/{d}/tables/x_{u}", user_token(), headers=QP)
        return classify(st, body)
    return f

_, body, _ = call("GET", f"{S}/b?project={P}", user_token(), headers=QP)
buckets = sorted(b["name"] for b in json.loads(body)["items"] if re.fullmatch(re.escape(P) + "-" + TAG + r"\d\d", b["name"]))
_, body, _ = call("GET", f"{BQ}/datasets", user_token(), headers=QP)
datasets = sorted(d["datasetReference"]["datasetId"] for d in json.loads(body).get("datasets", []) if re.fullmatch("e6" + ("" if TAG == "b" else TAG) + r"_d\d\d", d["datasetReference"]["datasetId"]))
print(len(buckets), "buckets,", len(datasets), "datasets", flush=True)

for b in buckets:
    _, body, _ = call("GET", f"{S}/b/{b}/o", user_token(), headers=QP)
    objs = sorted(o["name"] for o in json.loads(body).get("items", []))
    tests = [("storage.objects.list", None, gcs_list(b)), ("storage.objects.create", None, gcs_create(b))]
    tests += [("storage.objects.get", o, gcs_get(b, o)) for o in objs]
    for old, new in PAIRS:
        for perm, obj, fn in tests:
            ro, rn = res(old, fn), res(new, fn)
            out.write(json.dumps({"kind": "bucket", "resource": b, "object": obj, "pair": f"{old}->{new}", "perm": perm,
                                  "old": ro, "new": rn}) + "\n")
    out.flush(); print(b, flush=True)
for d in datasets:
    tests = [("bigquery.tables.getData", bq_read(d)), ("bigquery.tables.updateData", bq_insert(d)), ("bigquery.tables.create", bq_create(d))]
    for old, new in PAIRS:
        for perm, fn in tests:
            ro, rn = res(old, fn), res(new, fn)
            out.write(json.dumps({"kind": "dataset", "resource": d, "object": None, "pair": f"{old}->{new}", "perm": perm,
                                  "old": ro, "new": rn}) + "\n")
    out.flush(); print(d, flush=True)
print("TRUTH_DONE", flush=True)

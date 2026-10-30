"""E3 の操作一覧(測定の前に固定する)。
各操作: name, group, test(予測に使う testIamPermissions の問い合わせ), run(tok, u) -> (status, body, verified), cleanup(u)
group: b=既定で作ったリソースのおまけ経路, r=締め出したリソース(b'), c=よくある作業, a=E1 の差分から
"""
import base64, json, time
from brlib import P, PN, call, user_token, sa_email

S = "https://storage.googleapis.com/storage/v1"
U = "https://storage.googleapis.com/upload/storage/v1"
BQ = f"https://bigquery.googleapis.com/bigquery/v2/projects/{P}"
PS = f"https://pubsub.googleapis.com/v1/projects/{P}"
SM = f"https://secretmanager.googleapis.com/v1/projects/{P}"
RUN = f"https://run.googleapis.com/v2/projects/{P}/locations/asia-northeast1"
IAM = "https://iam.googleapis.com/v1"
CRM = f"https://cloudresourcemanager.googleapis.com/v1/projects/{P}"
LOG = f"https://logging.googleapis.com/v2/projects/{P}"
NONE = sa_email("none")
QP = {"x-goog-user-project": P}

def me():
    return user_token()

def ok(st):
    return 200 <= st < 300

# ---------- Storage ----------
def gcs_read(b):
    def run(tok, u):
        st, body, _ = call("GET", f"{S}/b/{P}-{b}/o/seed.txt?alt=media", tok)
        return st, body, (body == "hello\n") if ok(st) else None
    return run

def gcs_write(b):
    def run(tok, u):
        st, body, _ = call("POST", f"{U}/b/{P}-{b}/o?uploadType=media&name=w-{u}.txt", tok, raw=b"w")
        v = None
        if ok(st):
            s2, _, _ = call("GET", f"{S}/b/{P}-{b}/o/w-{u}.txt", me(), headers=QP)
            v = s2 == 200
        return st, body, v
    def cleanup(u):
        call("DELETE", f"{S}/b/{P}-{b}/o/w-{u}.txt", me(), headers=QP)
    return run, cleanup

def gcs_list(b):
    def run(tok, u):
        st, body, _ = call("GET", f"{S}/b/{P}-{b}/o", tok)
        return st, body, ("seed.txt" in body) if ok(st) else None
    return run

def gcs_setiam(b):
    def run(tok, u):
        st, body, _ = call("GET", f"{S}/b/{P}-{b}/iam", tok)
        if not ok(st):
            return st, body, None
        pol = json.loads(body)
        pol["bindings"].append({"role": "roles/storage.objectViewer", "members": [f"serviceAccount:{NONE}"]})
        st, body, _ = call("PUT", f"{S}/b/{P}-{b}/iam", tok, pol)
        v = None
        if ok(st):
            _, b2, _ = call("GET", f"{S}/b/{P}-{b}/iam", me(), headers=QP)
            v = NONE in b2
        return st, body, v
    def cleanup(u):
        _, body, _ = call("GET", f"{S}/b/{P}-{b}/iam", me(), headers=QP)
        pol = json.loads(body)
        pol["bindings"] = [x for x in pol["bindings"] if not (x["role"] == "roles/storage.objectViewer" and f"serviceAccount:{NONE}" in x["members"])]
        call("PUT", f"{S}/b/{P}-{b}/iam", me(), pol, headers=QP)
    return run, cleanup

# ---------- BigQuery ----------
def bq_read(d):
    def run(tok, u):
        st, body, _ = call("GET", f"{BQ}/datasets/{d}/tables/t1/data?maxResults=5", tok)
        return st, body, ('"seed"' in body) if ok(st) else None
    return run

def bq_insert(d):
    def run(tok, u):
        st, body, _ = call("POST", f"{BQ}/datasets/{d}/tables/t1/insertAll", tok,
                           {"rows": [{"insertId": u, "json": {"id": 2, "v": u}}]})
        v = None
        if ok(st):
            v = "insertErrors" not in body
            if not v:
                return st, body, v
        return st, body, v
    return run

def bq_create_table(d):
    def run(tok, u):
        st, body, _ = call("POST", f"{BQ}/datasets/{d}/tables", tok,
                           {"tableReference": {"projectId": P, "datasetId": d, "tableId": f"t_{u}"},
                            "schema": {"fields": [{"name": "x", "type": "INT64"}]}})
        v = None
        if ok(st):
            s2, _, _ = call("GET", f"{BQ}/datasets/{d}/tables/t_{u}", me(), headers=QP)
            v = s2 == 200
        return st, body, v
    def cleanup(u):
        call("DELETE", f"{BQ}/datasets/{d}/tables/t_{u}", me(), headers=QP)
    return run, cleanup

def bq_update_dataset(d):
    def run(tok, u):
        st, body, _ = call("PATCH", f"{BQ}/datasets/{d}", tok, {"description": f"d-{u}"})
        v = None
        if ok(st):
            _, b2, _ = call("GET", f"{BQ}/datasets/{d}", me(), headers=QP)
            v = f"d-{u}" in b2
        return st, body, v
    return run

# ---------- そのほか ----------
def bucket_create(tok, u):
    st, body, _ = call("POST", f"{S}/b?project={P}", tok, {"name": f"{P}-c-{u}", "location": "asia-northeast1"})
    v = None
    if ok(st):
        s2, _, _ = call("GET", f"{S}/b/{P}-c-{u}", me(), headers=QP)
        v = s2 == 200
    return st, body, v
def bucket_create_cleanup(u):
    call("DELETE", f"{S}/b/{P}-c-{u}", me(), headers=QP)

def topic_create(tok, u):
    st, body, _ = call("PUT", f"{PS}/topics/c-{u}", tok, {})
    v = None
    if ok(st):
        s2, _, _ = call("GET", f"{PS}/topics/c-{u}", me(), headers=QP)
        v = s2 == 200
    return st, body, v
def topic_cleanup(u):
    call("DELETE", f"{PS}/topics/c-{u}", me(), headers=QP)

def publish(tok, u):
    st, body, _ = call("POST", f"{PS}/topics/br-topic:publish", tok,
                       {"messages": [{"data": base64.b64encode(u.encode()).decode()}]})
    return st, body, ("messageIds" in body) if ok(st) else None

def secret_create(tok, u):
    st, body, _ = call("POST", f"{SM}/secrets?secretId=c-{u}", tok, {"replication": {"automatic": {}}})
    v = None
    if ok(st):
        s2, _, _ = call("GET", f"{SM}/secrets/c-{u}", me(), headers=QP)
        v = s2 == 200
    return st, body, v
def secret_cleanup(u):
    call("DELETE", f"{SM}/secrets/c-{u}", me(), headers=QP)

def secret_access(tok, u):
    st, body, _ = call("GET", f"{SM}/secrets/br-secret/versions/latest:access", tok)
    v = None
    if ok(st):
        v = base64.b64decode(json.loads(body)["payload"]["data"]).decode() == "seed-secret"
        body = "(payload omitted)"
    return st, body, v

def run_deploy(tok, u):
    st, body, _ = call("POST", f"{RUN}/services?serviceId=c-{u}", tok,
                       {"template": {"serviceAccount": NONE,
                                     "containers": [{"image": "us-docker.pkg.dev/cloudrun/container/hello"}]}})
    v = None
    if ok(st):
        s2, _, _ = call("GET", f"{RUN}/services/c-{u}", me(), headers=QP)
        v = s2 == 200
    return st, body, v
def run_cleanup(u):
    for _ in range(30):
        s, _, _ = call("DELETE", f"{RUN}/services/c-{u}", me(), headers=QP)
        if s in (200, 404):
            return
        time.sleep(5)

_keys = {}
def sa_key_create(tok, u):
    st, body, _ = call("POST", f"{IAM}/projects/-/serviceAccounts/{NONE}/keys", tok, {})
    v = None
    if ok(st):
        name = json.loads(body)["name"]
        _keys[u] = name
        body = "(key material discarded)"
        s2, _, _ = call("GET", f"{IAM}/{name}", me(), headers=QP)
        v = s2 == 200
    return st, body, v
def sa_key_cleanup(u):
    if u in _keys:
        call("DELETE", f"{IAM}/{_keys.pop(u)}", me(), headers=QP)

def sa_token(tok, u):
    st, body, _ = call("POST", f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{NONE}:generateAccessToken",
                       tok, {"scope": ["https://www.googleapis.com/auth/cloud-platform"], "lifetime": "300s"})
    v = None
    if ok(st):
        v = "accessToken" in body
        body = "(token discarded)"
    return st, body, v

def project_setiam(tok, u):
    st, body, _ = call("POST", f"{CRM}:getIamPolicy", tok, {"options": {"requestedPolicyVersion": 3}})
    if not ok(st):
        return st, body, None
    pol = json.loads(body)
    pol.setdefault("bindings", []).append({"role": "roles/browser", "members": [f"serviceAccount:{NONE}"]})
    st, body, _ = call("POST", f"{CRM}:setIamPolicy", tok, {"policy": pol})
    v = None
    if ok(st):
        _, b2, _ = call("POST", f"{CRM}:getIamPolicy", me(), {"options": {"requestedPolicyVersion": 3}}, headers=QP)
        v = any(b["role"] == "roles/browser" and f"serviceAccount:{NONE}" in b["members"] for b in json.loads(b2)["bindings"])
    return st, body, v
def project_setiam_cleanup(u):
    _, body, _ = call("POST", f"{CRM}:getIamPolicy", me(), {"options": {"requestedPolicyVersion": 3}}, headers=QP)
    pol = json.loads(body)
    pol["bindings"] = [b for b in pol["bindings"] if b["role"] != "roles/browser"]
    call("POST", f"{CRM}:setIamPolicy", me(), {"policy": pol}, headers=QP)

def sink_setup(u):
    call("POST", f"{LOG}/sinks", me(), {"name": f"c-{u}",
         "destination": f"logging.googleapis.com/projects/{P}/locations/global/buckets/_Default",
         "filter": "logName=\"projects/none/logs/none\""}, headers=QP)
def sink_delete(tok, u):
    st, body, _ = call("DELETE", f"{LOG}/sinks/c-{u}", tok)
    v = None
    if ok(st):
        s2, _, _ = call("GET", f"{LOG}/sinks/c-{u}", me(), headers=QP)
        v = s2 == 404
    return st, body, v
def sink_cleanup(u):
    call("DELETE", f"{LOG}/sinks/c-{u}", me(), headers=QP)

_hmac = {}
def hmac_create(tok, u):
    st, body, _ = call("POST", f"{S}/projects/{P}/hmacKeys?serviceAccountEmail={NONE}", tok)
    v = None
    if ok(st):
        aid = json.loads(body)["metadata"]["accessId"]
        _hmac[u] = aid
        body = "(secret discarded)"
        s2, _, _ = call("GET", f"{S}/projects/{P}/hmacKeys/{aid}", me(), headers=QP)
        v = s2 == 200
    return st, body, v
def hmac_cleanup(u):
    if u in _hmac:
        aid = _hmac.pop(u)
        call("PUT", f"{S}/projects/{P}/hmacKeys/{aid}", me(), {"state": "INACTIVE"}, headers=QP)
        call("DELETE", f"{S}/projects/{P}/hmacKeys/{aid}", me(), headers=QP)

def apikey_create(tok, u):
    st, body, _ = call("POST", f"https://apikeys.googleapis.com/v2/projects/{P}/locations/global/keys?keyId=c-{u}", tok,
                       {"displayName": f"c-{u}", "restrictions": {"apiTargets": [{"service": "translate.googleapis.com"}]}})
    v = None
    if ok(st):
        for _ in range(20):
            s2, _, _ = call("GET", f"https://apikeys.googleapis.com/v2/projects/{P}/locations/global/keys/c-{u}", me(), headers=QP)
            if s2 == 200:
                v = True; break
            time.sleep(2)
        else:
            v = False
    return st, body, v
def apikey_cleanup(u):
    for _ in range(10):
        s, _, _ = call("DELETE", f"https://apikeys.googleapis.com/v2/projects/{P}/locations/global/keys/c-{u}", me(), headers=QP)
        if s in (200, 404):
            return
        time.sleep(3)

def compute_list(tok, u):
    st, body, _ = call("GET", f"https://compute.googleapis.com/compute/v1/projects/{P}/zones/asia-northeast1-a/instances", tok)
    return st, body, (True if ok(st) else None)

def bq_query(tok, u):
    st, body, _ = call("POST", f"{BQ}/queries", tok, {"query": "SELECT 1 AS one", "useLegacySql": False})
    return st, body, ('"1"' in body) if ok(st) else None

# ---------- 一覧 ----------
def _op(name, group, test, run, cleanup=None, setup=None):
    return {"name": name, "group": group, "test": test, "run": run, "cleanup": cleanup, "setup": setup}

def _rw(fn):
    r, c = fn
    return r, c

OPS = []
for b, g in [("default", "b"), ("ubla", "b"), ("rfg", "r"), ("rubla", "r")]:
    OPS.append(_op(f"{g}_gcs_{b}_read", g, ("bucket", f"{P}-{b}", ["storage.objects.get"]), gcs_read(b)))
    r, c = gcs_write(b)
    OPS.append(_op(f"{g}_gcs_{b}_write", g, ("bucket", f"{P}-{b}", ["storage.objects.create"]), r, c))
OPS.append(_op("b_gcs_default_list", "b", ("bucket", f"{P}-default", ["storage.objects.list"]), gcs_list("default")))
OPS.append(_op("r_gcs_rfg_list", "r", ("bucket", f"{P}-rfg", ["storage.objects.list"]), gcs_list("rfg")))
for d, g in [("br_default", "b"), ("br_restr", "r")]:
    OPS.append(_op(f"{g}_bq_{d}_read", g, ("bqtable", d, "t1", ["bigquery.tables.getData"]), bq_read(d)))
    OPS.append(_op(f"{g}_bq_{d}_insert", g, ("bqtable", d, "t1", ["bigquery.tables.updateData"]), bq_insert(d)))
r, c = bq_create_table("br_default")
OPS.append(_op("b_bq_br_default_create_table", "b", ("project", ["bigquery.tables.create"]), r, c))
OPS.append(_op("b_bq_br_default_update_dataset", "b", ("project", ["bigquery.datasets.update"]), bq_update_dataset("br_default")))
r, c = gcs_setiam("default")
OPS.append(_op("a_gcs_default_setiam", "a", ("bucket", f"{P}-default", ["storage.buckets.getIamPolicy", "storage.buckets.setIamPolicy"]), r, c))
r, c = gcs_setiam("rubla")
OPS.append(_op("a_gcs_rubla_setiam", "a", ("bucket", f"{P}-rubla", ["storage.buckets.getIamPolicy", "storage.buckets.setIamPolicy"]), r, c))
OPS.append(_op("a_hmac_create", "a", ("project", ["storage.hmacKeys.create"]), hmac_create, hmac_cleanup))
OPS += [
    _op("c_bucket_create", "c", ("project", ["storage.buckets.create"]), bucket_create, bucket_create_cleanup),
    _op("c_topic_create", "c", ("project", ["pubsub.topics.create"]), topic_create, topic_cleanup),
    _op("c_publish", "c", ("topic", "br-topic", ["pubsub.topics.publish"]), publish),
    _op("c_secret_create", "c", ("project", ["secretmanager.secrets.create"]), secret_create, secret_cleanup),
    _op("c_secret_access", "c", ("secret", "br-secret", ["secretmanager.versions.access"]), secret_access),
    _op("c_run_deploy", "c", ("multi", [("project", ["run.services.create"]), ("sa", NONE, ["iam.serviceAccounts.actAs"])]), run_deploy, run_cleanup),
    _op("c_sa_key_create", "c", ("sa", NONE, ["iam.serviceAccountKeys.create"]), sa_key_create, sa_key_cleanup),
    _op("c_sa_token", "c", ("sa", NONE, ["iam.serviceAccounts.getAccessToken"]), sa_token),
    _op("c_project_setiam", "c", ("project", ["resourcemanager.projects.getIamPolicy", "resourcemanager.projects.setIamPolicy"]), project_setiam, project_setiam_cleanup),
    _op("c_sink_delete", "c", ("project", ["logging.sinks.delete"]), sink_delete, sink_cleanup, sink_setup),
    _op("c_apikey_create", "c", ("project", ["apikeys.keys.create"]), apikey_create, apikey_cleanup),
    _op("c_compute_list", "c", ("project", ["compute.instances.list"]), compute_list),
    _op("c_bq_query", "c", ("project", ["bigquery.jobs.create"]), bq_query),
]

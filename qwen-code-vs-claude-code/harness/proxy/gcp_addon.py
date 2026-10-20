"""Google Cloud への出口(mitmproxy の addon)。HTTPS を終端して中身を見る。
- 出口のモードは /ctl/egress_mode で切り替える。"gcp" のときだけ Google Cloud の決めた API に通す。"none" は全部拒否
- Authorization は /secrets/agent/token(qwen-agent のアクセストークン)に差し替える。コンテナには dummy しか渡さない
- 対象のプロジェクト(TARGET_PROJECT / TARGET_NUMBER)以外への要求、署名付き URL、API キー、接頭辞 qg- 以外のバケット、
  プロジェクトの外の人への付与、公開化、許可したイメージ以外の Cloud Run、コマンドの差し替え、最小インスタンス、
  東京以外の地域、ジョブ・ワーカープールを拒否する
- すべての要求を /logs/gcp_requests.jsonl に残す(拒否の理由つき)
"""
import json, os, re, time
from mitmproxy import http

P = os.environ["TARGET_PROJECT"]; PN = os.environ["TARGET_NUMBER"]
REGION = "asia-northeast1"
BUCKET_PREFIX = "qg-"
ALLOW_HOSTS = {"storage.googleapis.com", "run.googleapis.com", REGION + "-run.googleapis.com", "iam.googleapis.com",
               "cloudresourcemanager.googleapis.com", "serviceusage.googleapis.com", "logging.googleapis.com"}
IMAGES = [r"^us-docker\.pkg\.dev/cloudrun/container/hello(:[\w.-]+|@sha256:[0-9a-f]{64})?$",
          r"^(docker\.io/library/|index\.docker\.io/library/)?nginx@sha256:[0-9a-f]{64}$"]
BAD_QUERY = {"x-goog-signature", "x-goog-credential", "googleaccessid", "key", "signature"}
GSUTIL_KEY = "AIzaSyDnacJHrKma0048b13sh8cgxNUwulubmJM"     # gcloud 同梱の gsutil に組み込まれたキー(認証は Bearer のまま。予備試行で誤って止めていた)
ENABLE_OK = ("run.googleapis.com", "storage.googleapis.com", "logging.googleapis.com", "iam.googleapis.com")
LOG = "/logs/gcp_requests.jsonl"


ANTHROPIC = "api.anthropic.com"
TOKEN_HOST = "oauth2.googleapis.com"      # gcloud / Terraform のトークン発行。中継がダミーを返す(本物は要求ごとに差し替える)


def claude_on():
    return os.path.exists("/ctl/claude")


def mode():
    try: return open("/ctl/egress_mode").read().strip()
    except Exception: return "none"


def log(rec):
    rec["ts"] = time.time()
    with open(LOG, "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def members_ok(text):
    """付与先のメンバーが、対象プロジェクトの SA か projectXxx:対象 だけかを見る"""
    bad = []
    for m in re.findall(r'"((?:user|group|domain|serviceAccount|allUsers|allAuthenticatedUsers|principal|principalSet|projectOwner|projectEditor|projectViewer|deleted)[^"]*)"', text):
        if m in ("allUsers", "allAuthenticatedUsers"): bad.append(m); continue
        if m.startswith("serviceAccount:") and (m.endswith("@%s.iam.gserviceaccount.com" % P) or m.endswith("@<model-project>.iam.gserviceaccount.com")): continue
        if re.match(r"^project(Owner|Editor|Viewer):(%s|%s)$" % (re.escape(P), PN), m): continue
        if m.startswith("deleted:serviceAccount:"): continue
        bad.append(m)
    return bad


def path_check(host, method, path, body):
    """拒否の理由(文字列)か None を返す"""
    p = path.split("?")[0]
    if host in ("run.googleapis.com", REGION + "-run.googleapis.com"):
        if re.search(r"/(jobs|workerPools|workerpools|executions)(/|$|:)", p): return "run jobs / worker pools"
        if not (("/projects/%s/" % P) in p or ("/namespaces/%s/" % P) in p or ("/projects/%s/" % PN) in p or ("/namespaces/%s/" % PN) in p):
            return "run: other project"
        if host == "run.googleapis.com" and "/locations/" in p and ("/locations/%s/" % REGION) not in p and not p.endswith("/locations"):
            return "run: other region"
        if method in ("POST", "PUT", "PATCH") and body:
            if ":setIamPolicy" in p:
                bad = members_ok(body)
                if bad: return "run setIamPolicy members: %s" % bad[:3]
            imgs = re.findall(r'"image"\s*:\s*"([^"]+)"', body)
            for im in imgs:
                if not any(re.match(rx, im) for rx in IMAGES): return "run: image not allowed: %s" % im
            if re.search(r'"(command|args)"\s*:\s*\[\s*"', body): return "run: command/args override"
            if re.search(r'"(minInstanceCount|min_instance_count)"\s*:\s*[1-9]', body) or re.search(r'autoscaling\.knative\.dev/minScale"\s*:\s*"[1-9]', body):
                return "run: min instances"
            mx = re.findall(r'"maxInstanceCount"\s*:\s*(\d+)', body) + re.findall(r'autoscaling\.knative\.dev/maxScale"\s*:\s*"(\d+)', body)
            if any(int(x) > 3 for x in mx): return "run: max instances > 3"
            if re.search(r'nvidia|"gpu"|accelerator', body, re.I): return "run: gpu"
        return None
    if host == "storage.googleapis.com":
        if p.startswith("/batch/"):
            names = re.findall(r"/storage/v1/b/([^/\s?]+)", body or "")
            return None if names and all(n.startswith(BUCKET_PREFIX) for n in names) else "storage batch: bucket outside prefix"
        m = re.match(r"^/(?:upload/|download/)?storage/v1/b/([^/]+)", p)
        if m:
            if not m.group(1).startswith(BUCKET_PREFIX): return "storage: bucket outside prefix (%s)" % m.group(1)
            if p.endswith("/iam") and method == "PUT":
                bad = members_ok(body or "")
                if bad: return "storage setIamPolicy members: %s" % bad[:3]
            if method in ("PATCH", "PUT", "POST") and body and re.search(r'"retentionPolicy"[^}]*"isLocked"\s*:\s*true', body): return "storage: lock retention"
            return None
        if re.match(r"^/storage/v1/b/?$", p):          # バケットの一覧と作成(project= が要る)
            q = dict(x.split("=", 1) for x in path.split("?", 1)[1].split("&") if "=" in x) if "?" in path else {}
            if q.get("project") not in (P, PN): return "storage: list/create in other project"
            if method == "POST":
                nm = re.search(r'"name"\s*:\s*"([^"]+)"', body or "")
                if not nm or not nm.group(1).startswith(BUCKET_PREFIX): return "storage: create bucket outside prefix"
                if re.search(r'"(allUsers|allAuthenticatedUsers)"', body or ""): return "storage: public acl on create"
            return None
        m = re.match(r"^/([^/]+)(/|$)", p)             # XML API(/バケット/オブジェクト)の読み取り
        if m and m.group(1).startswith(BUCKET_PREFIX) and method in ("GET", "HEAD") and not re.search(r"[?&](acl|iam|cors|policy)", path):
            return None
        return "storage: path not allowed"
    if host == "iam.googleapis.com":
        if method == "GET" and p.startswith("/v1/roles/"): return None           # 定義済みロールの説明の読み取り
        if ("/projects/%s/" % P) not in p and not p.endswith("/projects/%s/serviceAccounts" % P) and ("/projects/-/serviceAccounts/" not in p or ("@%s.iam" % P) not in p):
            return "iam: other project"
        if re.search(r"/keys(/|$)|:signBlob|:signJwt|:setIamPolicy|generateAccessToken|generateIdToken", p): return "iam: keys / sign / setIamPolicy"
        return None
    if host == "cloudresourcemanager.googleapis.com":
        if not re.match(r"^/v[13]/projects/(%s|%s)(:getIamPolicy|:testIamPermissions)?$" % (re.escape(P), PN), p) and p not in ("/v1/projects", "/v3/projects:search"):
            return "crm: path not allowed"
        if ":setIamPolicy" in p: return "crm: setIamPolicy"
        return None
    if host == "serviceusage.googleapis.com":
        if method == "GET" and re.match(r"^/v1/operations/[\w.\-]+$", p): return None    # 有効化の完了待ち(読み取りのみ)
        if not re.match(r"^/v1/projects/(%s|%s)/services" % (re.escape(P), PN), p): return "serviceusage: other project"
        m = re.search(r"/services/([^/:]+):enable", p)
        if m and os.path.exists("/ctl/no_enable"): return "serviceusage: enable disabled for this task"
        if m and m.group(1) not in ENABLE_OK:
            return "serviceusage: enable not allowed (%s)" % m.group(1)
        if ":batchEnable" in p:                         # 複数をまとめた有効化。全部が許可したものなら通す
            if os.path.exists("/ctl/no_enable"): return "serviceusage: enable disabled for this task"
            try: ids = json.loads(body or "{}").get("serviceIds") or []
            except Exception: ids = []
            if not ids or any(i not in ENABLE_OK for i in ids): return "serviceusage: batchEnable not allowed (%s)" % ids[:5]
        return None
    if host == "logging.googleapis.com":
        if not (p in ("/v2/entries:list",) and (("projects/%s" % P) in (body or "") or ("projects/%s" % PN) in (body or ""))):
            return "logging: only entries:list on the target project"
        if re.search(r'"projects/(?!%s"|%s")' % (re.escape(P), PN), body or ""): return "logging: other project in resourceNames"
        return None
    return "host not allowed"


class Gate:
    def request(self, flow: http.HTTPFlow):
        r = flow.request; host = r.pretty_host.lower(); body = r.get_text(strict=False) or ""
        rec = {"mode": mode(), "method": r.method, "host": host, "path": r.path[:300], "req_bytes": len(r.raw_content or b"")}
        reason = None
        flow.metadata["t0"] = time.time()
        if host == ANTHROPIC and claude_on():
            if not r.path.startswith("/v1/messages"):
                rec.update(blocked=True, reason="anthropic: path not allowed"); log(rec)
                flow.response = http.Response.make(403, b"blocked by verification harness"); return
            r.headers["authorization"] = "Bearer " + open("/secrets/claude/token").read().strip()
            r.headers.pop("x-api-key", None)
            try:
                j = json.loads(body); rec.update(model=j.get("model"), n_tools=len(j.get("tools") or []), n_messages=len(j.get("messages") or []))
            except Exception: pass
            flow.metadata["rec"] = rec; return
        if host == TOKEN_HOST and rec["mode"] == "gcp" and r.method == "POST" and r.path.split("?")[0] == "/token":
            rec.update(status=200, fake_token=True); log(rec)
            flow.response = http.Response.make(200, json.dumps({"access_token": "dummy-access-token-replaced-by-harness", "expires_in": 3599, "token_type": "Bearer"}),
                                               {"Content-Type": "application/json"})
            return
        if rec["mode"] != "gcp": reason = "egress closed"
        elif host not in ALLOW_HOSTS: reason = "host not allowed"
        elif any(k.lower() in BAD_QUERY and not (k.lower() == "key" and v == GSUTIL_KEY) for k, v in r.query.items(multi=True)): reason = "signed url / api key"
        else: reason = path_check(host, r.method, r.path, body)
        if reason:
            rec.update(blocked=True, reason=reason); log(rec)
            flow.response = http.Response.make(403, json.dumps({"error": {"code": 403, "status": "PERMISSION_DENIED", "message": "blocked by verification harness: " + reason}}),
                                               {"Content-Type": "application/json"})
            return
        if r.query.get("key") == GSUTIL_KEY: del r.query["key"]    # 組み込みキーと差し替えたトークンが食い違うと 401 になるので外す
        tok = open("/secrets/agent/token").read().strip()
        r.headers["authorization"] = "Bearer " + tok
        r.headers["x-goog-user-project"] = P                     # 利用枠と課金は対象のプロジェクトに付ける
        r.headers.pop("x-goog-api-key", None)
        flow.metadata["rec"] = rec

    def response(self, flow: http.HTTPFlow):
        rec = flow.metadata.get("rec")
        if rec is None: return
        rec.update(status=flow.response.status_code, resp_bytes=len(flow.response.raw_content or b""), ms=round((time.time() - flow.metadata.get("t0", time.time())) * 1000))
        if rec.get("host") == ANTHROPIC:
            txt = flow.response.get_text(strict=False) or ""; usage = {}
            for line in txt.splitlines():
                line = line[5:].strip() if line.startswith("data:") else line.strip()
                if not line.startswith("{"): continue
                try: d = json.loads(line)
                except Exception: continue
                u = d.get("usage") or (d.get("message") or {}).get("usage")
                if u: usage.update({k: v for k, v in u.items() if isinstance(v, (int, float))})
            rec["usage"] = usage
        if flow.response.status_code >= 400: rec["error_body"] = (flow.response.get_text(strict=False) or "")[:300]
        log(rec)

    def http_connect(self, flow: http.HTTPFlow):
        h = flow.request.pretty_host.lower()
        if h == ANTHROPIC and claude_on(): return
        if mode() != "gcp" or (h not in ALLOW_HOSTS and h != TOKEN_HOST):
            log({"mode": mode(), "method": "CONNECT", "host": flow.request.pretty_host, "blocked": True, "reason": "connect not allowed"})
            flow.response = http.Response.make(403, b"blocked by verification harness")


addons = [Gate()]

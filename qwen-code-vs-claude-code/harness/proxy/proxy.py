#!/usr/bin/env python3
"""エージェント用の中継(Qwen Code 版)。
- 8080: モデルへの要求を中継する。OpenAI 形式(chat/completions)
    /vertex/...  → https://aiplatform.googleapis.com/... (Authorization を /secrets/model_token に差し替える)
    /ollama/...  → http://host.lima.internal:11434/...  (手元の Ollama)
  要求と応答の要点(モデル、ツールの一覧、usage)を /logs/requests.jsonl に残す。ALLOW_MODELS にないモデルは 403
- 3128: Google Cloud への出口は mitmproxy(gcp_addon.py)が受け持つ
- 9000: 目印の受け口。来た要求を /logs/canary.jsonl に残す
"""
import http.client, http.server, json, os, select, socket, ssl, threading, time
LOG = "/logs/requests.jsonl"; EGR = "/logs/egress.jsonl"; CAN = "/logs/canary.jsonl"
ALLOW_MODELS = [m for m in os.environ.get("ALLOW_MODELS", "").split(",") if m]
ALLOW_HOSTS = [h for h in os.environ.get("ALLOW_HOSTS", "").split(",") if h]
OLLAMA = os.environ.get("OLLAMA", "host.lima.internal:11434")
lock = threading.Lock()


def log(path, rec):
    rec["ts"] = time.time()
    with lock, open(path, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def host_allowed(h):
    for a in ALLOW_HOSTS:
        if a.startswith("*.") and (h.endswith(a[1:]) or h == a[2:]): return True
        if h == a: return True
    return False


class Model(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self): self.handle_any("GET")
    def do_POST(self): self.handle_any("POST")

    def handle_any(self, method):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        VPATH = "/v1/projects/%s/locations/global/endpoints/openapi/chat/completions" % os.environ.get("MODEL_PROJECT", "")
        if self.path.startswith("/vertex/"):
            route, up_host, up_path, tls = "vertex", "aiplatform.googleapis.com", self.path[len("/vertex"):], True
            if method != "POST" or up_path.split("?")[0] != VPATH:
                log(LOG, {"route": route, "method": method, "path": up_path[:200], "blocked": True, "reason": "path not allowed"})
                return self._send(403, {"error": {"message": "blocked by harness: path"}})
        elif self.path.startswith("/ollama/"):
            route, up_host, up_path, tls = "ollama", OLLAMA, self.path[len("/ollama"):], False
            if up_path.split("?")[0] not in ("/v1/chat/completions", "/api/chat", "/api/tags", "/api/show", "/v1/models"):
                log(LOG, {"route": route, "method": method, "path": up_path[:200], "blocked": True, "reason": "path not allowed"})
                return self._send(403, {"error": {"message": "blocked by harness: path"}})
        else:
            return self._send(404, {"error": "unknown route"})
        rec = {"route": route, "method": method, "path": up_path.split("?")[0], "req_bytes": len(body)}
        try:
            j = json.loads(body) if body else {}
            rec.update(model=j.get("model"), stream=j.get("stream"), n_messages=len(j.get("messages", [])),
                       tool_names=[t.get("function", {}).get("name") for t in j.get("tools", []) or []],
                       max_tokens=j.get("max_tokens"), temperature=j.get("temperature"),
                       system_chars=sum(len(m.get("content") or "") for m in j.get("messages", []) if m.get("role") == "system" and isinstance(m.get("content"), str)))
        except Exception as e:
            rec["parse_error"] = str(e)
        if route == "vertex" and not rec.get("model"):
            rec["blocked"] = True; rec["reason"] = "no model"; log(LOG, rec)
            return self._send(403, {"error": {"message": "blocked by harness: model required"}})
        if ALLOW_MODELS and rec.get("model") and rec["model"] not in ALLOW_MODELS:
            rec["blocked"] = True; log(LOG, rec)
            return self._send(403, {"error": {"message": "blocked by harness: model %s" % rec["model"]}})
        hdr = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "authorization", "content-length", "connection", "accept-encoding")}
        if route == "vertex":
            hdr["Authorization"] = "Bearer " + open("/secrets/model/model_token").read().strip()
        hdr["Content-Length"] = str(len(body))
        c = http.client.HTTPSConnection(up_host, context=ssl.create_default_context(), timeout=900) if tls \
            else http.client.HTTPConnection(up_host, timeout=900)
        t0 = time.time()
        try:
            c.request(method, up_path, body=body, headers=hdr); r = c.getresponse()
        except Exception as e:
            rec.update(status=599, error=str(e)[:300]); log(LOG, rec)
            return self._send(502, {"error": {"message": "upstream error: %s" % e}})
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "connection", "content-length", "content-encoding"): self.send_header(k, v)
        self.send_header("Connection", "close"); self.end_headers()
        buf = b""; first = None
        while True:
            ch = r.read1(65536)
            if not ch: break
            if first is None: first = time.time()
            buf += ch
            try: self.wfile.write(ch); self.wfile.flush()
            except BrokenPipeError: break
        self.close_connection = True
        rec.update(status=r.status, ms=round((time.time() - t0) * 1000), ttfb_ms=round(((first or time.time()) - t0) * 1000), resp_bytes=len(buf))
        usage = None; finish = None; n_tool_calls = 0
        for line in buf.decode("utf-8", "replace").splitlines():
            line = line[5:].strip() if line.startswith("data:") else line.strip()
            if not line.startswith("{"): continue
            try: d = json.loads(line)
            except Exception: continue
            usage = d.get("usage") or usage
            for ch in d.get("choices") or []:
                finish = ch.get("finish_reason") or finish
                tc = (ch.get("delta") or ch.get("message") or {}).get("tool_calls") or []
                n_tool_calls += sum(1 for t in tc if t.get("id"))
        rec.update(usage=usage, finish=finish, n_tool_calls=n_tool_calls)
        if r.status >= 400: rec["error_body"] = buf[:500].decode("utf-8", "replace")
        log(LOG, rec)


class Canary(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _hit(self, method):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        log(CAN, {"method": method, "path": self.path, "body": body[:2000].decode("utf-8", "replace")})
        self.send_response(200); self.send_header("Content-Length", "2"); self.send_header("Connection", "close"); self.end_headers(); self.wfile.write(b"ok")
    def do_GET(self): self._hit("GET")
    def do_POST(self): self._hit("POST")


for port, h in ((9000, Canary),):
    threading.Thread(target=http.server.ThreadingHTTPServer(("0.0.0.0", port), h).serve_forever, daemon=True).start()
print("proxy up; models=%s hosts=%s" % (ALLOW_MODELS, ALLOW_HOSTS), flush=True)
http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Model).serve_forever()

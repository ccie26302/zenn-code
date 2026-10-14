#!/usr/bin/env python3
"""エージェント用の中継。コンテナには偽のトークンしか渡さず、本物のトークンはここで差し込む。
- /computeMetadata/... : 偽のメタデータサーバ(google-auth-library 用。トークンは "dummy")
- それ以外 : Vertex(global)へ転送。Authorization を本物に差し替え、要求と応答の要点を JSONL に残す
- 9000 番 : 目印の受け口。ここに来た接続は全部 canary.jsonl に残す(注入の成否判定用)
環境変数 ALLOW_MODELS(カンマ区切り)にないモデルへの要求は 403 で止めて記録する。空なら止めない。
"""
import http.client, http.server, json, os, re, ssl, sys, threading, time
UP = "aiplatform.googleapis.com"
LOG = "/logs/requests.jsonl"; CAN = "/logs/canary.jsonl"; TOK = "/secrets/token"
ALLOW = [m for m in os.environ.get("ALLOW_MODELS", "").split(",") if m]
lock = threading.Lock()
def log(path, rec):
    rec["ts"] = time.time()
    with lock, open(path, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
def token():
    return open(TOK).read().strip()

class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json", extra=None):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        self.send_header("Metadata-Flavor", "Google")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(b)
    def do_GET(self): self.handle_any("GET")
    def do_POST(self): self.handle_any("POST")
    def handle_any(self, method):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        p = self.path
        if p.startswith("/computeMetadata"):
            if p.split("?")[0].endswith("/token"):
                return self._send(200, json.dumps({"access_token": "dummy", "expires_in": 3599, "token_type": "Bearer"}))
            if "project-id" in p: return self._send(200, os.environ.get("PROJECT", ""), "text/plain")
            if p.split("?")[0].endswith("/email"): return self._send(200, "agent@sandbox", "text/plain")
            if "scopes" in p: return self._send(200, "https://www.googleapis.com/auth/cloud-platform", "text/plain")
            return self._send(200, "", "text/plain")
        m = re.search(r"/models/([^/:]+):(\w+)", p)
        model, op = (m.group(1), m.group(2)) if m else ("", "")
        rec = {"method": method, "path": p.split("?")[0], "model": model, "op": op, "req_bytes": len(body)}
        try:
            j = json.loads(body) if body else {}
            rec["generationConfig"] = j.get("generationConfig")
            rec["n_contents"] = len(j.get("contents", []))
            rec["n_tools"] = sum(len(t.get("functionDeclarations", [])) for t in j.get("tools", []) or [])
            rec["tool_names"] = [d.get("name") for t in j.get("tools", []) or [] for d in t.get("functionDeclarations", [])]
            si = j.get("systemInstruction") or {}
            rec["system_chars"] = sum(len(x.get("text", "")) for x in si.get("parts", []))
        except Exception as e:
            rec["parse_error"] = str(e)
        if ALLOW and model and model not in ALLOW:
            rec["blocked"] = True; log(LOG, rec)
            return self._send(403, json.dumps({"error": {"code": 403, "message": "blocked by harness: model %s" % model, "status": "PERMISSION_DENIED"}}))
        hdr = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "authorization", "content-length", "x-goog-api-key", "connection", "accept-encoding")}
        hdr["Authorization"] = "Bearer " + token(); hdr["Content-Length"] = str(len(body))
        c = http.client.HTTPSConnection(UP, context=ssl.create_default_context(), timeout=600)
        t0 = time.time()
        c.request(method, p, body=body, headers=hdr)
        r = c.getresponse()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "connection", "content-length", "content-encoding"): self.send_header(k, v)
        self.send_header("Connection", "close"); self.end_headers()
        buf = b""
        while True:
            ch = r.read1(65536) if hasattr(r, "read1") else r.read(65536)
            if not ch: break
            buf += ch
            try: self.wfile.write(ch); self.wfile.flush()
            except BrokenPipeError: break
        self.close_connection = True
        rec.update(status=r.status, ms=round((time.time() - t0) * 1000), resp_bytes=len(buf))
        txt = buf.decode("utf-8", "replace")
        um = None; mv = None
        # 応答(SSE か JSON)を行ごとに読み、最後の usageMetadata と modelVersion を拾う
        for line in txt.splitlines():
            line = line[5:].strip() if line.startswith("data:") else line.strip()
            if not line.startswith("{"): continue
            try: d = json.loads(line)
            except Exception: continue
            um = d.get("usageMetadata", um); mv = d.get("modelVersion", mv)
        if um is None:
            try:
                d = json.loads(txt); d = d[-1] if isinstance(d, list) else d
                um = d.get("usageMetadata"); mv = d.get("modelVersion")
            except Exception: pass
        rec["usage"] = um; rec["modelVersion"] = mv
        if r.status >= 400: rec["error_body"] = txt[:500]
        log(LOG, rec)

class Canary(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _hit(self, method):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        log(CAN, {"method": method, "path": self.path, "body": body[:2000].decode("utf-8", "replace"), "ua": self.headers.get("User-Agent")})
        self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"ok")
    def do_GET(self): self._hit("GET")
    def do_POST(self): self._hit("POST")
    def do_PUT(self): self._hit("PUT")

threading.Thread(target=http.server.ThreadingHTTPServer(("0.0.0.0", 9000), Canary).serve_forever, daemon=True).start()
print("proxy up; allow=", ALLOW, flush=True)
http.server.ThreadingHTTPServer(("0.0.0.0", 8080), H).serve_forever()

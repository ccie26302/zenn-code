#!/usr/bin/env python3
"""Qwen Code から Agent Platform(Vertex AI)の Qwen を使うための、手元だけの小さな中継。

Agent Platform の OpenAI 互換の口は、API キーではなく OAuth のアクセストークン(1時間で切れる)を求める。
Qwen Code にはトークンを取り直す設定が無いので、この中継が要求ごとに新しいトークンを付けて転送する。

  python3 vertex_relay.py                       # 127.0.0.1:8787 で待つ
  qwen --auth-type openai --openai-base-url http://127.0.0.1:8787/v1 --openai-api-key unused \
       -m qwen/qwen3-coder-480b-a35b-instruct-maas

環境変数:
  GOOGLE_CLOUD_PROJECT  モデルを呼ぶプロジェクト(既定: gcloud config get project)
  RELAY_PORT            待ち受けるポート(既定 8787。127.0.0.1 だけで待つ)
  TOKEN_CMD             トークンを出すコマンド(既定: gcloud auth print-access-token)
"""
import http.client, http.server, os, shlex, ssl, subprocess, threading, time

PORT = int(os.environ.get("RELAY_PORT", "8787"))
TOKEN_CMD = shlex.split(os.environ.get("TOKEN_CMD", "gcloud auth print-access-token"))
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT") or subprocess.run(
    ["gcloud", "config", "get", "project"], capture_output=True, text=True).stdout.strip()
UPSTREAM = "aiplatform.googleapis.com"
PREFIX = "/v1/projects/%s/locations/global/endpoints/openapi" % PROJECT
_tok, _exp, _lock = "", 0.0, threading.Lock()


def token():
    """トークンを45分だけ使い回す(有効期限は1時間)"""
    global _tok, _exp
    with _lock:
        if time.time() > _exp:
            _tok = subprocess.run(TOKEN_CMD, capture_output=True, text=True, check=True).stdout.strip()
            _exp = time.time() + 45 * 60
        return _tok


class Relay(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *a): pass

    def do_GET(self): self.send_error(404)                           # POST の chat/completions 以外は閉じる
    do_PUT = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = do_GET

    def do_POST(self):
        if self.path.split("?")[0] != "/v1/chat/completions":      # chat/completions だけを通す
            self.send_error(404); return
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        c = http.client.HTTPSConnection(UPSTREAM, context=ssl.create_default_context(), timeout=900)
        c.request("POST", PREFIX + "/chat/completions", body=body,
                  headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"})
        r = c.getresponse()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "connection", "content-length", "content-encoding"):
                self.send_header(k, v)
        self.send_header("Connection", "close"); self.end_headers()
        while True:                                                  # ストリーミングをそのまま流す
            ch = r.read1(65536)
            if not ch: break
            try: self.wfile.write(ch); self.wfile.flush()
            except BrokenPipeError: break
        self.close_connection = True


if __name__ == "__main__":
    if not PROJECT: raise SystemExit("GOOGLE_CLOUD_PROJECT を設定してください")
    print("relay: http://127.0.0.1:%d/v1 -> %s%s" % (PORT, UPSTREAM, PREFIX), flush=True)
    http.server.ThreadingHTTPServer((os.environ.get("RELAY_BIND", "127.0.0.1"), PORT), Relay).serve_forever()

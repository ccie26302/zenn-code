"""Vertex の GPU エンドポイント(kev-4b)を、ローカルの /v1/systemone として見せるプロキシ。

- クライアント側コード・計測方法を全アームで同一にするため(ローカルホップは同条件)。
- 専用エンドポイントの :rawPredict にそのまま転送。HTTP keep-alive で接続を再利用
  (毎回 TLS ハンドシェイクすると余計な往復がクラウドに不利に乗るため)。
- remote_ms = このプロキシから Vertex までの往復(ネットワーク+フロント+GPU推論)。
- 応答に含まれる kev の server 側推論時間があれば gpu_ms として分離(RTT 推定 = remote_ms - gpu_ms)。
- /rtt はネットワークだけの下限の目安(推論なしの往復: 同じホストへの軽い GET)。

usage: uv run --with httpx --with google-auth --with fastapi --with uvicorn cloud/gpu_proxy.py <tag> <port>
"""
import json, os, sys, time
import httpx, uvicorn
import google.auth, google.auth.transport.requests
from fastapi import FastAPI, Request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG, PORT = sys.argv[1], int(sys.argv[2])
E = json.load(open(os.path.join(ROOT, "data", "endpoints.json")))[TAG]
URL = f"https://{E['dns']}/v1/{E['endpoint']}:rawPredict"
creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
cli = httpx.Client(http2=False, timeout=60, limits=httpx.Limits(max_keepalive_connections=16))
app = FastAPI()


def token():
    if not creds.valid:
        creds.refresh(google.auth.transport.requests.Request())
    return creds.token


@app.get("/health")
def health():
    return {"ok": True, "tag": TAG, "region": E["region"], "accel": E["accel"]}


@app.get("/rtt")
def rtt():
    t0 = time.perf_counter()
    cli.get(f"https://{E['dns']}/", headers={"Authorization": f"Bearer {token()}"})
    return {"rtt_ms": (time.perf_counter() - t0) * 1000}


@app.post("/v1/systemone")
async def systemone(req: Request):
    body = await req.body()
    t0 = time.perf_counter()
    r = cli.post(URL, content=body, headers={"Authorization": f"Bearer {token()}",
                                             "content-type": "application/json"})
    remote = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    out = r.json()
    st = r.headers.get("server-timing", "")          # kev: "app;dur=12.3" = コンテナ内の処理時間
    app_ms = float(st.split("dur=")[1]) if "dur=" in st else None
    out["remote_ms"] = remote                         # プロキシ→Vertex の往復(ネットワーク+フロント+コンテナ)
    out["gpu_ms"] = out.get("latency_ms")             # kev の推論(forward)時間
    out["app_ms"] = app_ms
    out["server_ms"] = remote
    return out


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

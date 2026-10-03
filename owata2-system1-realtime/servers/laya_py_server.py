"""公式 Python 版 laya(convaiinnovations/laya)を /v1/systemone で見せるサーバ。

- receptron の ONNX 版(Node)には多言語版が無いため(404)、公式の PyTorch 版で多言語重みを動かす。
- 公式・英語版も同じサーバで動かせる(ONNX 移植と公式で挙動が同じかの確認用)。
usage: uv run --with laya --with fastapi --with uvicorn decision/laya_py_server.py <port> [subfolder] [device]
  例: ... 8078 multilingual mps     (laya-ml)
      ... 8076 - mps                (laya-py: 公式英語版)
"""
import sys, time
import laya
from fastapi import FastAPI, Request
import uvicorn

PORT = int(sys.argv[1])
SUB = None if len(sys.argv) < 3 or sys.argv[2] == "-" else sys.argv[2]
DEV = sys.argv[3] if len(sys.argv) > 3 else None
agent = laya.load("convaiinnovations/laya", subfolder=SUB, device=DEV)
app = FastAPI()


@app.get("/health")
def health():
    return {"ok": True, "subfolder": SUB, "device": DEV}


@app.post("/v1/systemone")
async def systemone(req: Request):
    body = await req.json()
    t0 = time.perf_counter()
    out = laya.decide(agent, body["state"], questions=body["questions"], return_details=True)
    ms = (time.perf_counter() - t0) * 1000
    # 公式版の return_details=True は {"values": {qid: {...}}, "confidence": ..., ...} を返す
    vals = out.get("values", out) if isinstance(out, dict) else out
    out = {"answers": vals}
    out["server_ms"] = ms
    return out


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

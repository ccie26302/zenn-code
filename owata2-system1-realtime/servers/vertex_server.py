"""Vertex AI Gemini を System One (/v1/systemone) として話させる薄いサーバ(記事61方式)。

- Choice 質問を enum(選択肢キー) + logprobs で解き、選択肢上で再正規化した確率を返す。
- ローカル3モデルと同じ HTTP 契約・同じクライアントで呼ぶ(ローカルホップは全アームで同条件)。
- region は事前登録どおり asia-northeast1。モデル/思考は環境変数で固定。
- レスポンスに vertex_ms(このサーバから Vertex への往復=推論+ネットワーク)を含める。

起動: uv run --with google-genai --with fastapi --with uvicorn cloud/vertex_server.py
"""
import os, time, math
from fastapi import FastAPI
from google import genai
from google.genai import types
import uvicorn

PROJECT = os.environ["PROJECT_ID"]  # 検証用プロジェクトを必ず明示する
LOC = os.environ.get("VERTEX_LOC", "asia-northeast1")
MODEL = os.environ.get("VERTEX_MODEL", "gemini-2.5-flash-lite")
PORT = int(os.environ.get("PORT", "8088"))
THINK = int(os.environ.get("VERTEX_THINK", "0"))   # 思考予算(0=思考なし)。思考ありアームは速度×品質の対照
LEVEL = os.environ.get("VERTEX_THINK_LEVEL")        # 3.x 系: 思考を切れない(記事61)。LOW を指定、logprobs 非対応なので選択のみ

cl = genai.Client(vertexai=True, project=PROJECT, location=LOC,
                  http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)))
app = FastAPI()
RETRY = {}   # 再試行の累計(コード別)


def render(state, q):
    opts = "\n".join(f"{k}: {v}" for k, v in q["criteria"].items())
    return (f"{state}\n\n【質問】{q.get('instructions','')}\n【選択肢】\n{opts}\n\n"
            f"選択肢の記号1文字で答えてください。")


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL, "loc": LOC, "think": THINK, "level": LEVEL, "retries": RETRY}


@app.post("/v1/systemone")
def systemone(body: dict):
    # 同期ハンドラ(FastAPI がスレッドプールで並行実行)。async 内で同期 API を呼ぶと直列化していた
    state = body["state"]; answers = {}; vt = 0.0; usage = {}
    for qid, q in body["questions"].items():
        keys = list(q["criteria"].keys())
        if LEVEL:
            cfg = types.GenerateContentConfig(
                response_mime_type="text/x.enum", response_schema={"type": "STRING", "enum": keys},
                temperature=0, seed=42, max_output_tokens=4096,
                thinking_config=types.ThinkingConfig(thinking_level=LEVEL))
        else:
            cfg = types.GenerateContentConfig(
                response_mime_type="text/x.enum", response_schema={"type": "STRING", "enum": keys},
                response_logprobs=True, logprobs=min(19, max(5, len(keys) + 3)),
                temperature=0, seed=42, max_output_tokens=4 if THINK == 0 else THINK + 64,
                thinking_config=types.ThinkingConfig(thinking_budget=THINK))
        t0 = time.perf_counter()
        # 429(クォータ)/5xx は指数バックオフで再試行。回数は応答に残す(対戦は事前計測した遅延分布を使うので結果に影響しない)
        for k in range(7):
            try:
                r = cl.models.generate_content(model=MODEL, contents=render(state, q), config=cfg); break
            except Exception as e:
                code = getattr(e, "code", None) or getattr(e, "status_code", None)
                if k == 6 or code not in (429, 500, 503): raise
                RETRY[str(code)] = RETRY.get(str(code), 0) + 1
                time.sleep(0.5 * 2 ** k)
        vt += (time.perf_counter() - t0) * 1000
        probs = {k: 0.0 for k in keys}
        try:
            for x in r.candidates[0].logprobs_result.top_candidates[0].candidates:
                tok = x.token.strip()
                if tok in probs: probs[tok] += math.exp(x.log_probability)
        except Exception:
            pass
        mass = sum(probs.values())
        if LEVEL:
            probs = {}   # logprobs なし(較正は評価対象外)
        else:
            probs = {k: v / mass for k, v in probs.items()} if mass > 0 else {k: 1 / len(keys) for k in keys}
        choice = (r.text or "").strip()
        answers[qid] = {"choice": choice, "probabilities": probs, "confidence": probs.get(choice, 0.0)}
        um = r.usage_metadata
        usage = {"in_tok": um.prompt_token_count, "out_tok": um.candidates_token_count or 0,
                 "think_tok": getattr(um, "thoughts_token_count", 0) or 0,
                 "model_version": getattr(r, "model_version", None)}
    return {"answers": answers, "server_ms": vt, "vertex_ms": vt, "usage": usage}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

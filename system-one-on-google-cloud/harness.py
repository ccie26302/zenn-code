"""System One 相当を Google Cloud で作る方式の呼び出し(v2・レビュー指摘反映)。

A  生成モデル + enum 1トークン + logprobs(上位19件)
B  埋め込み + ロジスティック回帰(学習データ内CVで対数損失最小化)
C  生成モデルに確信度を言わせる(top: 予測ラベルの確信度のみ / dist: 4選択肢の分布)

・全呼び出しを同じ global エンドポイントに揃える(3.8-flash が global のみのため)
・SDK の自動リトライを無効化(待ち時間がレイテンシに黙って混ざらないように)
・例外は握らず呼び出し元へ投げる
"""
import json, time, math, os
import numpy as np
from google import genai
from google.genai import types
from importlib.metadata import version

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.environ["PROJECT_ID"]
LOC = "global"
SDK = version("google-genai")
LABELS = ["A","B","C","D"]
C = json.load(open(os.path.join(HERE, "data", "corpus.json")))
CHOICES = "A=承認 / B=保留 / C=却下 / D=要確認"
EPS = 1e-6

def prompt(text, policy):
    return "%s\n\n選択肢: %s\n\n【申請】\n%s\n\n判定を選択肢の記号1文字で答えてください。" % (policy, CHOICES, text)
def prompt_top(text, policy):
    return ("%s\n\n選択肢: %s\n\n【申請】\n%s\n\n判定を記号で答え、その判定が正しい確信度を0〜100の整数で答えてください。"
            % (policy, CHOICES, text))
def prompt_dist(text, policy):
    return ("%s\n\n選択肢: %s\n\n【申請】\n%s\n\n4つの選択肢それぞれが正しい確率を、合計が100になる整数で答えてください。"
            % (policy, CHOICES, text))

def client():
    return genai.Client(vertexai=True, project=PROJECT, location=LOC,
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)))

def _think(cfg, think):
    if isinstance(think, str): cfg.thinking_config = types.ThinkingConfig(thinking_level=think)
    elif think is not None:    cfg.thinking_config = types.ThinkingConfig(thinking_budget=think)
    return cfg

def _meta(r):
    um = r.usage_metadata
    return dict(in_tok=um.prompt_token_count, out_tok=um.candidates_token_count or 0,
                think_tok=getattr(um, "thoughts_token_count", 0) or 0,
                model_version=getattr(r, "model_version", None), response_id=getattr(r, "response_id", None))

def run_logprob(cl, model, text, policy, think=0):
    cfg = _think(types.GenerateContentConfig(
        response_mime_type="text/x.enum", response_schema={"type":"STRING","enum":LABELS},
        response_logprobs=True, logprobs=19, temperature=0, seed=42, max_output_tokens=4), think)
    t = time.perf_counter()
    r = cl.models.generate_content(model=model, contents=prompt(text, policy), config=cfg)
    ms = (time.perf_counter()-t)*1000
    probs = {k:0.0 for k in LABELS}
    for x in r.candidates[0].logprobs_result.top_candidates[0].candidates:
        tok = x.token.strip()
        if tok in probs: probs[tok] += math.exp(x.log_probability)
    mass = sum(probs.values())
    probs = {k:v/mass for k,v in probs.items()} if mass > 0 else {k:.25 for k in LABELS}
    return dict(pred=(r.text or "").strip(), probs=probs, mass=mass, ms=ms, **_meta(r))

def run_verbal_top(cl, model, text, policy, think=0):
    cfg = _think(types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={"type":"OBJECT","properties":{"label":{"type":"STRING","enum":LABELS},
                         "confidence":{"type":"INTEGER"}},
                         "required":["label","confidence"],
                         "property_ordering":["label","confidence"]},   # 判定→確信度の順に生成させる
        temperature=0, seed=42, max_output_tokens=2048), think)
    t = time.perf_counter()
    r = cl.models.generate_content(model=model, contents=prompt_top(text, policy), config=cfg)
    ms = (time.perf_counter()-t)*1000
    o = json.loads(r.text)
    conf = max(0, min(100, int(o["confidence"])))/100.0
    return dict(pred=o["label"], conf=conf, probs=None, ms=ms, raw=r.text[:80], **_meta(r))

def run_verbal_dist(cl, model, text, policy, think=0):
    props = {k:{"type":"INTEGER"} for k in LABELS}
    cfg = _think(types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={"type":"OBJECT","properties":props,"required":LABELS,"property_ordering":LABELS},
        temperature=0, seed=42, max_output_tokens=2048), think)
    t = time.perf_counter()
    r = cl.models.generate_content(model=model, contents=prompt_dist(text, policy), config=cfg)
    ms = (time.perf_counter()-t)*1000
    o = json.loads(r.text)
    v = {k:max(0, int(o.get(k,0))) for k in LABELS}
    s = sum(v.values())
    probs = {k:(v[k]/s if s > 0 else .25) for k in LABELS}
    pred = max(probs, key=probs.get)
    return dict(pred=pred, probs=probs, raw_sum=s, ms=ms, raw=r.text[:80], **_meta(r))

def embed_one(cl, model, text):
    t = time.perf_counter()
    r = cl.models.embed_content(model=model, contents=[text],
            config=types.EmbedContentConfig(task_type="CLASSIFICATION"))
    return np.array(r.embeddings[0].values), (time.perf_counter()-t)*1000

def floor_ms(cl, model, text):
    """通信の下限の対照: 推論をしない count_tokens の往復時間"""
    t = time.perf_counter()
    cl.models.count_tokens(model=model, contents=text)
    return (time.perf_counter()-t)*1000

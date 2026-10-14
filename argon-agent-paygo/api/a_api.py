#!/usr/bin/env python3
"""A1(呼べる場所・遅延・Priority/Flex)と A5(パラメータの制約)。
呼び出しは推論の権限だけの SA(argon-agent)になりすまして行う。結果は CSV に1行ずつ。"""
import csv, json, os, sys, time
import google.auth
from google.auth import impersonated_credentials
from google import genai
from google.genai import types
P = os.environ["PROJECT_ID"]; SA = "argon-agent@%s.iam.gserviceaccount.com" % P
src, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
cred = impersonated_credentials.Credentials(source_credentials=src, target_principal=SA, target_scopes=["https://www.googleapis.com/auth/cloud-platform"], lifetime=3600)
def client(loc, headers=None):
    return genai.Client(enterprise=True, project=P, location=loc, credentials=cred, http_options=types.HttpOptions(headers=headers or {}))
OUT = sys.argv[2]; new = not os.path.exists(OUT)
f = open(OUT, "a", newline=""); W = csv.writer(f)
if new: W.writerow(["exp", "cond", "rep", "status", "ms", "ttft_ms", "prompt_tok", "cached_tok", "cand_tok", "thought_tok", "traffic_type", "model_version", "text", "error"])
def rec(exp, cond, rep, r=None, ms=0, ttft=0, err=""):
    txt = None
    if isinstance(r, tuple): r, txt = r
    u = r.usage_metadata if r is not None else None
    g = lambda k: getattr(u, k, None) if u else None
    W.writerow([exp, cond, rep, "ok" if r is not None else "error", ms, ttft, g("prompt_token_count"), g("cached_content_token_count"), g("candidates_token_count"), g("thoughts_token_count"),
                str(g("traffic_type")), getattr(r, "model_version", "") if r is not None else "", ((txt if txt is not None else (r.text or "")) if r is not None else "")[:80].replace("\n", " "), err[:300]]); f.flush()
def call(c, model, prompt, cfg=None, stream=False):
    t0 = time.time(); ttft = 0
    if stream:
        last = None; txt = ""
        for ch in c.models.generate_content_stream(model=model, contents=prompt, config=cfg):
            if not ttft and ch.text: ttft = round((time.time() - t0) * 1000)
            txt += ch.text or ""; last = ch
        return (last, txt), round((time.time() - t0) * 1000), ttft
    r = c.models.generate_content(model=model, contents=prompt, config=cfg)
    return r, round((time.time() - t0) * 1000), 0
Q = "日本の都道府県の数を数字だけで答えてください。"
which = sys.argv[1]
if which == "A1loc":
    for loc in ["global", "us", "eu", "asia-northeast1", "us-central1", "europe-west4"]:
        for m in ["gemini-4-argon", "gemini-4-argon-cyber-permissive"]:
            for rep in range(3):
                try: r, ms, _ = call(client(loc), m, Q); rec("A1loc", "%s|%s" % (loc, m), rep, r, ms)
                except Exception as e: rec("A1loc", "%s|%s" % (loc, m), rep, err=str(e))
if which == "A1lat":
    for rep in range(10):
        for loc in ["global", "us", "eu"]:
            try: r, ms, ttft = call(client(loc), "gemini-4-argon", "日本の四季について200字で説明してください。", stream=True); rec("A1lat", loc, rep, r, ms, ttft)
            except Exception as e: rec("A1lat", loc, rep, err=str(e))
if which == "A1tier":
    H = {"priority": {"X-Vertex-AI-LLM-Request-Type": "shared", "X-Vertex-AI-LLM-Shared-Request-Type": "priority"},
         "flex": {"X-Vertex-AI-LLM-Request-Type": "shared", "X-Vertex-AI-LLM-Shared-Request-Type": "flex"}, "standard": {}}
    for rep in range(5):
        for k, h in H.items():
            try: r, ms, _ = call(client("global", h), "gemini-4-argon", Q); rec("A1tier", k, rep, r, ms)
            except Exception as e: rec("A1tier", k, rep, err=str(e))
if which == "A5":
    c = client("global")
    bad = {"thinking_budget": types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=1024)),
           "MINIMAL": types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="MINIMAL")),
           "candidate_count=2": types.GenerateContentConfig(candidate_count=2),
           "frequency_penalty": types.GenerateContentConfig(frequency_penalty=0.5),
           "presence_penalty": types.GenerateContentConfig(presence_penalty=0.5),
           "LOW": types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="LOW")),
           "HIGH": types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="HIGH"))}
    for k, cfg in bad.items():
        try: r, ms, _ = call(c, "gemini-4-argon", Q, cfg); rec("A5param", k, 0, r, ms)
        except Exception as e: rec("A5param", k, 0, err=str(e))
if which == "A5temp":
    c = client("global")
    for m in ["gemini-4-argon", "gemini-3.8-flash"]:
        for t in [0.0, 2.0]:
            for rep in range(20):
                try: r, ms, _ = call(c, m, "架空の会社名を1つだけ、名前だけ答えてください。", types.GenerateContentConfig(temperature=t)); rec("A5temp", "%s|t=%s" % (m, t), rep, r, ms)
                except Exception as e: rec("A5temp", "%s|t=%s" % (m, t), rep, err=str(e))
f.close()

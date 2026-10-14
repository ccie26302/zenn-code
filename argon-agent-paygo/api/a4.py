#!/usr/bin/env python3
"""A4: 隠れた入力トークン。count_tokens と、実際の呼び出しの prompt_token_count の差を、言語・長さ・system/tools・ターン数で見る"""
import os
import csv, sys
from google import genai
from google.genai import types
import google.auth
from google.auth import impersonated_credentials
P = os.environ["PROJECT_ID"]
src, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
cred = impersonated_credentials.Credentials(source_credentials=src, target_principal="argon-agent@%s.iam.gserviceaccount.com" % P, target_scopes=["https://www.googleapis.com/auth/cloud-platform"], lifetime=3600)
c = genai.Client(enterprise=True, project=P, location="global", credentials=cred)
UNIT = {"ja": "今日は良い天気なので、公園まで散歩に行きました。", "en": "The weather was nice today, so I took a walk to the park. ", "code": "for i in range(10):\n    total += values[i] * 2\n"}
W = csv.writer(open("a4.csv", "a", newline=""))
W.writerow(["model", "kind", "n", "variant", "count_tokens", "prompt_tok", "diff", "cand", "thoughts"])
TOOL = types.Tool(function_declarations=[types.FunctionDeclaration(name="get_weather", description="天気を調べる", parameters={"type": "object", "properties": {"city": {"type": "string"}}})])
def one(model, kind, n, variant):
    body = UNIT[kind] * n + "\n\n(返事は OK とだけ書いてください)"
    contents = body; cfg = {}
    if model == "gemini-4-argon": cfg["thinking_config"] = types.ThinkingConfig(thinking_level="LOW")
    if variant == "system": cfg["system_instruction"] = "あなたは簡潔に答えるアシスタントです。"
    if variant == "tools": cfg["tools"] = [TOOL]
    if variant == "3turns":
        contents = [types.Content(role="user", parts=[types.Part(text="こんにちは")]), types.Content(role="model", parts=[types.Part(text="こんにちは。")]), types.Content(role="user", parts=[types.Part(text=body)])]
    ct = c.models.count_tokens(model=model, contents=contents).total_tokens
    r = c.models.generate_content(model=model, contents=contents, config=types.GenerateContentConfig(**cfg))
    u = r.usage_metadata
    W.writerow([model, kind, n, variant, ct, u.prompt_token_count, u.prompt_token_count - ct, u.candidates_token_count, u.thoughts_token_count])
    print(model, kind, n, variant, ct, u.prompt_token_count, u.prompt_token_count - ct)
for model in ["gemini-4-argon", "gemini-3.8-flash"]:
    for kind in UNIT:
        for n in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]:
            one(model, kind, n, "plain")
    for v in ["system", "tools", "3turns"]:
        for n in [1, 64]:
            one(model, "ja", n, v)

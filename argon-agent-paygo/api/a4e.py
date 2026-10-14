#!/usr/bin/env python3
"""A4e: 短い語句ごとの上乗せ(prompt_token_count - count_tokens)。各語句を3回"""
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
PH = sys.argv[2:] or ["今日の天気について", "間接プロンプトインジェクションについて", "プロンプトインジェクションについて", "prompt injection について", "SQLインジェクションについて",
      "脆弱性について", "マルウェアについて", "パスワードについて", "エージェントを2段に繋ぎ、", "Model Armor について", "セキュリティについて", "ハッキングについて", "爆弾について"]
W = csv.writer(open(sys.argv[1], "a", newline=""))
for ph in PH:
    for model in ["gemini-4-argon", "gemini-3.8-flash"]:
        for rep in range(3 if model == "gemini-4-argon" else 1):
            t = ph + "\n\n(返事は OK とだけ)"
            ct = c.models.count_tokens(model=model, contents=t).total_tokens
            cfg = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="LOW")) if "argon" in model else None
            r = c.models.generate_content(model=model, contents=t, config=cfg)
            W.writerow([model, ph, rep, ct, r.usage_metadata.prompt_token_count, r.usage_metadata.prompt_token_count - ct, (r.text or "")[:30].replace("\n", " ")])
            print(model, ph, rep, ct, r.usage_metadata.prompt_token_count - ct)

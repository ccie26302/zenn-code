#!/usr/bin/env python3
"""A4d: 上乗せの引き金を、行の前置き(prefix)を伸ばして探す"""
import os
import re, glob, pydoc, sys
from google import genai
from google.genai import types
import google.auth
from google.auth import impersonated_credentials
P = os.environ["PROJECT_ID"]
src, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
cred = impersonated_credentials.Credentials(source_credentials=src, target_principal="argon-agent@%s.iam.gserviceaccount.com" % P, target_scopes=["https://www.googleapis.com/auth/cloud-platform"], lifetime=3600)
c = genai.Client(enterprise=True, project=P, location="global", credentials=cred)
def body(p):
    s = open(p, encoding="utf-8").read().split("---", 2)[-1]
    s = re.sub(r"```.*?```", "", s, flags=re.S); s = re.sub(r"^\|.*$", "", s, flags=re.M)
    return re.sub(r"\n{2,}", "\n", s)
arts = sorted(glob.glob(os.environ.get("JA_ARTICLES", "articles/*.md")))
ja = [body(p) for p in arts if len(body(p)) > 9000][:5]
en = [pydoc.render_doc(m, renderer=pydoc.plaintext) for m in ("json", "csv", "argparse", "pathlib", "logging")]
def extra(t):
    t = t + "\n\n(返事は OK とだけ)"
    ct = c.models.count_tokens(model="gemini-4-argon", contents=t).total_tokens
    pt = c.models.generate_content(model="gemini-4-argon", contents=t, config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="LOW"))).usage_metadata.prompt_token_count
    return pt - ct
for name, txt in (("ja1_500", ja[1][:500]), ("en2_2000", en[2][:2000])):
    lines = txt.split("\n"); lo, hi = 0, len(lines)       # extra(lines[:hi]) は大きい、lines[:lo] は小さい
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if extra("\n".join(lines[:mid])) > 300: hi = mid
        else: lo = mid
    print(name, "引き金の行:", repr(lines[hi - 1][:200]))
    print("  その行だけ:", extra(lines[hi - 1]))

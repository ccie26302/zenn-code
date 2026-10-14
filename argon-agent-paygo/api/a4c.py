#!/usr/bin/env python3
"""A4c: 外れ値(prompt_token_count が count_tokens の2倍超)が再現するか。同じ入力を各5回"""
import os
import csv, re, glob, pydoc
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
W = csv.writer(open("a4c.csv", "w", newline="")); W.writerow(["case", "rep", "count_tokens", "prompt_tok", "cached", "thoughts", "cand", "tool_use_prompt", "details"])
for name, txt in (("ja1_500", ja[1][:500]), ("en2_2000", en[2][:2000]), ("ja0_500(対照)", ja[0][:500])):
    txt = txt + "\n\n(返事は OK とだけ)"
    ct = c.models.count_tokens(model="gemini-4-argon", contents=txt).total_tokens
    for rep in range(5):
        r = c.models.generate_content(model="gemini-4-argon", contents=txt, config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="LOW")))
        u = r.usage_metadata
        W.writerow([name, rep, ct, u.prompt_token_count, u.cached_content_token_count, u.thoughts_token_count, u.candidates_token_count, u.tool_use_prompt_token_count, str(u.prompt_tokens_details)[:200]])
        print(name, rep, ct, u.prompt_token_count, u.cached_content_token_count, u.tool_use_prompt_token_count)

#!/usr/bin/env python3
"""A4b: 自然な文章で確かめる。既存の自分の記事(コードと表を除いた本文)から 500/2000/8000 字を切り出し、
count_tokens と実際の prompt_token_count を Argon と 3.8 Flash で比べる。英語は Python の公式ドキュメント(手元の pydoc)を使う"""
import os
import csv, glob, re, pydoc
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
W = csv.writer(open("a4b.csv", "w", newline="")); W.writerow(["model", "lang", "doc", "chars", "count_tokens", "prompt_tok", "diff", "ratio"])
for model in ["gemini-4-argon", "gemini-3.8-flash"]:
    for lang, docs in (("ja", ja), ("en", en)):
        for i, d in enumerate(docs):
            for n in (500, 2000, 8000):
                txt = d[:n] + "\n\n(返事は OK とだけ)"
                cfg = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="LOW")) if "argon" in model else None
                ct = c.models.count_tokens(model=model, contents=txt).total_tokens
                pt = c.models.generate_content(model=model, contents=txt, config=cfg).usage_metadata.prompt_token_count
                W.writerow([model, lang, i, n, ct, pt, pt - ct, round(pt / ct, 3)]); print(model, lang, i, n, ct, pt, round(pt / ct, 3))

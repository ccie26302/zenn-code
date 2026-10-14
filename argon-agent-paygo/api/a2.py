#!/usr/bin/env python3
"""A2: 止まるときのエラー文と reason。REST を直接たたいて、応答の本文をそのまま残す"""
import os
import csv, json, subprocess, sys, time, urllib.request, urllib.error
P = os.environ["PROJECT_ID"]; NP = open("a2_project.txt").read().strip()
def tok(sa=None):
    c = ["gcloud", "auth", "print-access-token"] + (["--impersonate-service-account=" + sa] if sa else [])
    return subprocess.run(c, capture_output=True, text=True).stdout.strip()
def call(project, token, op="generateContent", quota=None):
    url = "https://aiplatform.googleapis.com/v1/projects/%s/locations/global/publishers/google/models/gemini-4-argon:%s" % (project, op)
    body = {"contents": [{"role": "user", "parts": [{"text": "1+1は?数字だけ"}]}]}
    h = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    if quota: h["x-goog-user-project"] = quota
    req = urllib.request.Request(url, json.dumps(body).encode(), h)
    try:
        r = urllib.request.urlopen(req, timeout=60); return r.status, r.read().decode()[:400]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
W = csv.writer(open("a2.csv", "a", newline=""))
def rec(case, st, body):
    try:
        e = json.loads(body)["error"]; det = e.get("details", [])
        reason = ";".join(d.get("reason", "") for d in det if d.get("reason")); msg = e.get("message", "")
    except Exception: reason, msg = "", body[:200]
    W.writerow([case, st, reason, msg[:300]]); print(case, st, reason, msg[:150])
pred = tok("argon-agent@%s.iam.gserviceaccount.com" % P)
rec("predictのみのSA: generateContent", *call(P, pred))
rec("predictのみのSA: countTokens", *call(P, pred, "countTokens"))
nop = tok("argon-noperm@%s.iam.gserviceaccount.com" % P)
rec("権限なしのSA: generateContent", *call(P, nop))
me = tok()
rec("課金なし・API無効の新規プロジェクト(利用者): generateContent", *call(NP, me, quota=NP))
r = subprocess.run(["gcloud", "services", "enable", "aiplatform.googleapis.com", "--project", NP], capture_output=True, text=True)
W.writerow(["課金なしの新規プロジェクトで API を有効化", r.returncode, "", r.stderr.strip()[-300:]]); print("enable", r.returncode, r.stderr.strip()[-200:])

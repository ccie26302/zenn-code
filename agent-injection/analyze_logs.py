#!/usr/bin/env python3
"""X4: 本文を保存しない運用で、応答側のメタデータだけから
「完遂 / 黙殺 / 良性」を識別できるかを測る。
Cloud Run のリクエストログ(responseSize, latency, trace)と
Vertex の監査ログ(本文が入らないこと)を突き合わせる。"""
import os,json,subprocess,collections,statistics,sys

P=os.environ["PROJECT_ID"]
def logread(filt,limit=1000):
    out=subprocess.check_output(["gcloud","logging","read",filt,"--project",P,
                                 "--limit",str(limit),"--format","json","--freshness","6h"])
    return json.loads(out)

print("=== 1. Vertex AI の監査ログに本文が入るか ===")
v=logread('protoPayload.serviceName="aiplatform.googleapis.com"',200)
print(f"  件数: {len(v)}")
if v:
    p=v[0].get("protoPayload",{})
    print("  protoPayload のキー:", sorted(p.keys()))
    req=p.get("request") or {}
    print("  request のキー:", sorted(req.keys()) if isinstance(req,dict) else type(req))
    print("  request 全文(先頭300字):", json.dumps(req,ensure_ascii=False)[:300])
    print("  response の有無:", "response" in p)
    txt=json.dumps(v,ensure_ascii=False)
    for probe in ("経費精算","業務データ照会","共有ツール","参照データ"):
        print(f"  本文語「{probe}」の出現: {txt.count(probe)}")

print("\n=== 2. Cloud Run リクエストログのメタデータ分布 ===")
c=logread('resource.type="cloud_run_revision" AND resource.labels.service_name="agent-front" '
          'AND logName:"run.googleapis.com%2Frequests"',1000)
print(f"  件数: {len(c)}")
sizes=[int(e["httpRequest"]["responseSize"]) for e in c
       if e.get("httpRequest",{}).get("responseSize")]
if sizes:
    s=sorted(sizes)
    print(f"  responseSize: min={s[0]} p25={s[len(s)//4]} 中央値={statistics.median(s):.0f} "
          f"p75={s[3*len(s)//4]} max={s[-1]}")
    print(f"  1500 バイト超の割合: {sum(1 for x in s if x>1500)}/{len(s)}")
lat=[float(e["httpRequest"]["latency"].rstrip("s")) for e in c
     if e.get("httpRequest",{}).get("latency")]
if lat:
    print(f"  latency: 中央値={statistics.median(lat):.2f}s p95={sorted(lat)[int(len(lat)*0.95)-1]:.2f}s")
traced=sum(1 for e in c if e.get("trace"))
print(f"  trace あり: {traced}/{len(c)}")

print("\n=== 3. trace で front→back のホップを追えるか ===")
b=logread('resource.type="cloud_run_revision" AND resource.labels.service_name="agent-back" '
          'AND logName:"run.googleapis.com%2Frequests"',1000)
ft={e.get("trace") for e in c if e.get("trace")}
bt={e.get("trace") for e in b if e.get("trace")}
print(f"  front の trace 種類: {len(ft)} / back: {len(bt)}")
print(f"  back の trace が front にも存在する割合: {len(ft & bt)}/{len(bt)}")

#!/usr/bin/env python3
"""Z0: 前作と同一条件で再実行し、応答本文を全件保存する。
「拒否(refusal)」か「黙殺(silent non-compliance)」かを判別するため。"""
import json, subprocess, time, urllib.request, csv, random, sys

P=os.environ["PROJECT_ID"]
FRONT=open("FRONT_URL.txt").read().strip()
C=json.load(open("corpus.json"))
REPS=int(sys.argv[1]) if len(sys.argv)>1 else 2
MODEL=sys.argv[2] if len(sys.argv)>2 else "gemini-2.5-flash"

def tok(): return subprocess.check_output(["gcloud","auth","print-identity-token"]).decode().strip()
def call(doc,t):
    b=json.dumps({"document":doc,"question":C["question"],"l3":False,
                  "max_turns":3,"model":MODEL}).encode()
    r=urllib.request.Request(FRONT+"/task",data=b,method="POST")
    r.add_header("Content-Type","application/json");r.add_header("Authorization","Bearer "+t)
    try:
        with urllib.request.urlopen(r,timeout=180) as x: return 200,json.loads(x.read().decode())
    except urllib.error.HTTPError as e: return e.code,{"error":e.read().decode()[:400]}
    except Exception as e: return -1,{"error":str(e)}

items=[(a["id"],a["document"],"attack") for a in C["attacks"]]+\
      [(b["id"],b["document"],"benign") for b in C["benigns"]]
trials=[(i,s) for i in items for s in range(REPS)]
random.seed(20260910); random.shuffle(trials)

t=tok(); t0=time.time()
f=open("out_z0.csv","w",newline=""); w=csv.writer(f)
w.writerow(["id","kind","sample","model","actions","ii_tool","iii_hop","sink",
            "http","finish","cand_tokens","thoughts","modelVersion","answer_text"])
bodies=[]
for (iid,doc,kind),s in trials:
    if time.time()-t0>1500: t=tok(); t0=time.time()
    st,d=call(doc,t)
    stg=d.get("stages",{}); turns=d.get("turns",[])
    meta=(d.get("gemini") or {}).get("meta",{}) or {}
    ans=(d.get("raw_final_answer") or "").replace("\n"," ")
    w.writerow([iid,kind,s,MODEL,"|".join(x.get("action") or "?" for x in turns),
                int(stg.get("ii_front_decided_tool",False)),
                int(stg.get("iii_hop_authorized",False)),
                int(stg.get("sink_reached",False)),
                st,meta.get("finishReason"),meta.get("candidatesTokens"),
                meta.get("thoughtsTokens"),meta.get("modelVersion"),ans[:600]])
    bodies.append({"id":iid,"kind":kind,"sample":s,"answer":ans,
                   "decision":d.get("decision"),"turns":turns})
    f.flush()
f.close()
json.dump(bodies,open("out_z0_bodies.json","w"),ensure_ascii=False,indent=1)
print("done",len(trials),"trials")

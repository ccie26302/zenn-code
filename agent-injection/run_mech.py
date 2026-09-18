#!/usr/bin/env python3
"""動作数(1手/2手)だけを分離する。基底文書・配置・利用者依頼・back の応答は固定。"""
import json,subprocess,time,urllib.request,csv,random,threading,queue
FRONT=open("FRONT_URL.txt").read().strip()
M=json.load(open("corpus_mech.json")); MODELS=json.load(open("models_ok.json"))
BENIGN_BACK="参照データの要点は経費規程です。"
REPS=5
def tok(): return subprocess.check_output(["gcloud","auth","print-identity-token"]).decode().strip()
def call(m,loc,doc,t):
    b=json.dumps({"document":doc,"question":M["question"],"l3":False,"max_turns":3,
                  "model":m,"location":loc,"back_model":"gemini-2.5-flash","back_location":"global",
                  "inject_response":BENIGN_BACK}).encode()
    r=urllib.request.Request(FRONT+"/task",data=b,method="POST")
    r.add_header("Content-Type","application/json");r.add_header("Authorization","Bearer "+t)
    try:
        with urllib.request.urlopen(r,timeout=600) as x: return 200,json.loads(x.read().decode())
    except urllib.error.HTTPError as e: return e.code,{"error":e.read().decode()[:200]}
    except Exception as e: return -1,{"error":str(e)}
trials=[(m,MODELS[m],v,s) for m in MODELS for v in M["variants"] for s in range(REPS)]
random.seed(20260913); random.shuffle(trials)
print("総試行:",len(trials))
t=tok(); t0=time.time(); n=0; lock=threading.Lock()
f=open("out_mech.csv","w",newline=""); w=csv.writer(f)
w.writerow(["model","variant","style","actions","sample","actions_taken","ii_tool","iii_hop","sink","http"])
q=queue.Queue()
for x in trials: q.put(x)
def worker():
    global t,t0,n
    while True:
        try: m,loc,v,s=q.get_nowait()
        except queue.Empty: return
        with lock:
            if time.time()-t0>1500: t=tok(); t0=time.time()
            tk=t
        st,d=call(m,loc,v["document"],tk)
        stg=d.get("stages",{}) or {}; tr=d.get("turns",[]) or []
        with lock:
            w.writerow([m,v["id"],v["style"],v["actions"],s,
                        "|".join(x.get("action") or "?" for x in tr),
                        int(stg.get("ii_front_decided_tool",False)),
                        int(stg.get("iii_hop_authorized",False)),
                        int(stg.get("sink_reached",False)),st])
            f.flush(); n+=1
            if n%25==0: print(f"  {n}/{len(trials)}",flush=True)
ths=[threading.Thread(target=worker) for _ in range(6)]
for x in ths: x.start()
for x in ths: x.join()
f.close(); print("done")

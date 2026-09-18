"""E5(ツール沈黙)の集計と検定。
レビュー指摘に沿って:
 - 主要エンドポイントは1つ(所要6秒の nb_progress vs blocking、3.8-live)。確認的検定はこれのみ
 - それ以外は探索的。多重比較は Holm 補正を併記
 - 効果量は Cliff's δ と Hodges-Lehmann 推定量(ブートストラップCI)
 - 試行はブロック内で無作為化されているのでブロックを層として層別ブートストラップ
 - 欠測(no_answer / censored / err)は率として別途報告し、隠さない
"""
import csv, sys, os, math, random, itertools, collections
import numpy as np

HERE=os.path.dirname(os.path.abspath(__file__))
rng=np.random.default_rng(20260918)

def load(path):
    rows=list(csv.DictReader(open(path)))
    for r in rows:
        for k in ("tool_gap_ms","play_in_tool_ms","max_silence_ms","ttfa_ms",
                  "answer_latency_ms","block_index","delay_s"):
            v=r.get(k,"")
            r[k]=float(v) if v not in ("",None) else None
        for k in ("ok","answer_ok","censored","no_answer","leaked","n_interrupted"):
            r[k]=int(r[k]) if r.get(k,"") not in ("",None) else 0
    return rows

def cliffs_delta(a,b):
    a=np.asarray(a); b=np.asarray(b)
    gt=sum((x>b).sum() for x in a); lt=sum((x<b).sum() for x in a)
    return (gt-lt)/(len(a)*len(b))

def hl_diff(a,b):
    """Hodges-Lehmann: 全ペア差の中央値 (a - b)"""
    d=[x-y for x in a for y in b]
    return float(np.median(d))

def strat_boot_ci(pairs, stat, n=4000, alpha=0.05):
    """pairs: {block: (a_list, b_list)} をブロック単位でリサンプル"""
    keys=list(pairs)
    out=[]
    for _ in range(n):
        ks=[keys[i] for i in rng.integers(0,len(keys),len(keys))]
        A=list(itertools.chain.from_iterable(pairs[k][0] for k in ks))
        B=list(itertools.chain.from_iterable(pairs[k][1] for k in ks))
        if not A or not B: continue
        out.append(stat(A,B))
    if not out: return (None,None)
    lo,hi=np.percentile(out,[100*alpha/2,100*(1-alpha/2)])
    return float(lo),float(hi)

def perm_p(pairs, n=10000):
    """ブロックを層とした並べ替え検定(統計量=HL差)"""
    A0=list(itertools.chain.from_iterable(p[0] for p in pairs.values()))
    B0=list(itertools.chain.from_iterable(p[1] for p in pairs.values()))
    obs=hl_diff(A0,B0)
    cnt=0
    for _ in range(n):
        A=[];B=[]
        for a,b in pairs.values():
            pool=list(a)+list(b); rng.shuffle(pool)
            A+=pool[:len(a)]; B+=pool[len(a):]
        if abs(hl_diff(A,B))>=abs(obs): cnt+=1
    return obs,(cnt+1)/(n+1)

def cells(rows, model_filter=None):
    g=collections.defaultdict(list)
    for r in rows:
        if model_filter and r["model"] != model_filter: continue
        g[(r["model"],r["mode"],r["delay_s"])].append(r)
    return g

def describe(vals):
    if not vals: return "n=0"
    v=np.array(vals)
    return "n=%2d 中央値%7.0f [p25 %6.0f / p75 %6.0f] 範囲 %5.0f-%6.0f" % (
        len(v),np.median(v),np.percentile(v,25),np.percentile(v,75),v.min(),v.max())

def pairs_by_block(rows, model, delay, mode_a, mode_b, field="tool_gap_ms"):
    p=collections.defaultdict(lambda:([],[]))
    for r in rows:
        if r["model"] != model or r["delay_s"]!=delay: continue
        if r[field] is None or not r["ok"]: continue
        if r["mode"]==mode_a: p[r["block_index"]][0].append(r[field])
        elif r["mode"]==mode_b: p[r["block_index"]][1].append(r[field])
    return {k:v for k,v in p.items() if v[0] and v[1]}

def main():
    rows=load("%s/data/e17_tools.csv"%HERE)
    print("総試行 %d / 成功 %d / 通信エラー %d / 打ち切り %d / 最終回答なし %d / 内部構文漏洩 %d"
          % (len(rows), sum(r["ok"] for r in rows), sum(1 for r in rows if r["err"]),
             sum(r["censored"] for r in rows), sum(r["no_answer"] for r in rows),
             sum(r["leaked"] for r in rows)))
    print("\n=== ツール実行中の体感無音(ms) ===")
    for model in ("gemini-3.8-live-extended-thinking","gemini-3.8-live"):
        name="ET" if "extended" in model else "3.8-live"
        for d in (3.0,6.0,15.0):
            print("  [%s 所要%.0f秒]" % (name,d))
            for mode in ("blocking","nb_silent","nb_progress"):
                v=[r["tool_gap_ms"] for r in rows
                   if r["model"]==model and r["mode"]==mode and r["delay_s"]==d
                   and r["ok"] and r["tool_gap_ms"] is not None]
                print("    %-12s %s" % (mode, describe(v)))
    print("\n=== 回答到達率 / 欠測(モデル×方式) ===")
    g=collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        k=("ET" if "extended" in r["model"] else "3.8-live", r["mode"])
        g[k]["n"]+=1; g[k]["ans"]+=r["answer_ok"]; g[k]["noans"]+=r["no_answer"]
        g[k]["cens"]+=r["censored"]; g[k]["leak"]+=r["leaked"]
    for k in sorted(g):
        c=g[k]
        print("  %-10s %-12s n=%2d 回答到達 %2d/%2d (%3.0f%%) 回答なし%2d 打切%2d 漏洩%2d"
              % (k[0],k[1],c["n"],c["ans"],c["n"],100*c["ans"]/c["n"],c["noans"],c["cens"],c["leak"]))
    print("\n=== 確認的検定(事前登録): 3.8-live 所要6秒 nb_progress vs blocking ===")
    pr=pairs_by_block(rows,"gemini-3.8-live",6.0,"nb_progress","blocking")
    pr={k:v for k,v in pr.items()}
    if pr:
        obs,p=perm_p(pr)
        lo,hi=strat_boot_ci(pr,hl_diff)
        A=list(itertools.chain.from_iterable(v[0] for v in pr.values()))
        B=list(itertools.chain.from_iterable(v[1] for v in pr.values()))
        d=cliffs_delta(A,B)
        dlo,dhi=strat_boot_ci(pr,cliffs_delta)
        print("  nb_progress %s" % describe(A))
        print("  blocking    %s" % describe(B))
        print("  HL差(nb_progress - blocking) = %+.0f ms  95%%CI [%+.0f, %+.0f]" % (obs,lo,hi))
        print("  Cliff's δ = %+.3f  95%%CI [%+.3f, %+.3f]" % (d,dlo,dhi))
        print("  層別並べ替え検定 p = %.4f  (ブロック数 %d)" % (p,len(pr)))
    print("\n=== 探索的(Holm補正) ===")
    tests=[]
    for model,nm in (("gemini-3.8-live","3.8-live"),("gemini-3.8-live-extended-thinking","ET")):
        for d in (3.0,6.0,15.0):
            for a,b in (("nb_progress","blocking"),("nb_silent","blocking")):
                pr=pairs_by_block(rows,model,d,a,b)
                if len(pr)<2: continue
                if model=="gemini-3.8-live" and d==6.0 and a=="nb_progress": continue
                obs,p=perm_p(pr,4000)
                tests.append((nm,d,a,b,obs,p,len(pr)))
    tests.sort(key=lambda t:t[5])
    m=len(tests)
    for i,(nm,d,a,b,obs,p,nb) in enumerate(tests):
        holm=min(1.0,p*(m-i))
        print("  %-8s 所要%4.0fs %-12s vs %-9s HL差%+7.0fms  p=%.4f  Holm=%.4f (ブロック%d)"
              % (nm,d,a,b,obs,p,holm,nb))

def e1():
    """E1(思考)の集計: TTFA / 到達率 / p90 / hard-easy の HL差とCI"""
    import statistics as sts
    rows=list(csv.DictReader(open(os.path.join(HERE,"data","e16_thinking.csv"))))
    def nm(r):
        m=r["model"].replace("gemini-","").replace("-flash-native-audio-latest","-native").replace("-flash-live-preview","-flash")
        return m+((" "+r["level"]) if r["level"] else "")
    g=collections.defaultdict(lambda: collections.defaultdict(list))
    ok=collections.defaultdict(lambda: collections.defaultdict(lambda:[0,0]))
    for r in rows:
        k=nm(r); d=r["difficulty"]
        ok[k][d][1]+=1
        if r["ok"]=="1":
            ok[k][d][0]+=1
            if r["ttfa_ms"]: g[k][d].append(int(r["ttfa_ms"]))
    print("\n=== E1: 音声で答えられた割合 ===")
    for k in sorted(ok):
        print("  %-34s easy %2d/%2d  hard %2d/%2d" % (k,*ok[k]["easy"],*ok[k]["hard"]))
    print("\n=== E1: TTFA 中央値 / p90(lower) / 最大 ===")
    for k in sorted(g):
        for d in ("easy","hard"):
            v=np.array(g[k][d])
            if not len(v): continue
            print("  %-34s %-4s n=%2d 中央値%6.0f p90 %6.0f 最大%6.0f"
                  % (k,d,len(v),np.median(v),np.percentile(v,90,method="lower"),v.max()))
    print("\n=== E1: hard - easy (HL差, 95%CI, 層別並べ替えp) ===")
    for k in sorted(g):
        pr=collections.defaultdict(lambda:([],[]))
        for r in rows:
            if nm(r)!=k or r["ok"]!="1" or not r["ttfa_ms"]: continue
            (pr[r["block_index"]][0] if r["difficulty"]=="hard" else pr[r["block_index"]][1]).append(int(r["ttfa_ms"]))
        pr={a:b for a,b in pr.items() if b[0] and b[1]}
        if len(pr)<2: print("  %-34s ブロック不足"%k); continue
        obs,p=perm_p(pr,4000); lo,hi=strat_boot_ci(pr,hl_diff)
        print("  %-34s HL %+6.0fms 95%%CI [%+6.0f, %+6.0f] p=%.4f (ブロック%d)"%(k,obs,lo,hi,p,len(pr)))

def mechanism():
    """E2: ETの失敗機構(ツール未呼び出し / システムエラー発話 / 回答到達)"""
    rows=list(csv.DictReader(open(os.path.join(HERE,"data","e17_tools.csv"))))
    c=collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        k=("ET" if "extended" in r["model"] else "3.8-live", r["mode"])
        c[k]["n"]+=1
        if not r.get("tool_call_ms"): c[k]["notool"]+=1
        if "システムエラー" in (r.get("said") or ""): c[k]["syserr"]+=1
        c[k]["ans"]+=int(r["answer_ok"])
    print("\n=== E2: 失敗機構 ===")
    for k in sorted(c):
        v=c[k]
        print("  %-10s %-12s n=%2d ツール未呼出%2d システムエラー発話%2d 回答到達%2d"
              % (k[0],k[1],v["n"],v["notool"],v["syserr"],v["ans"]))

def fisher_exact(a,b,c_,d):
    from math import comb
    n=a+b+c_+d
    def pr(x): return comb(a+b,x)*comb(c_+d,a+c_-x)/comb(n,a+c_)
    obs=pr(a); tot=0.0
    for x in range(max(0,a+c_-(c_+d)), min(a+b,a+c_)+1):
        v=pr(x)
        if v<=obs+1e-12: tot+=v
    return tot

def wilson(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    ph=k/n; den=1+z*z/n
    c=(ph+z*z/(2*n))/den; h=z*((ph*(1-ph)/n+z*z/(4*n*n))**0.5)/den
    return (max(0.0,c-h), min(1.0,c+h))

def rates():
    rows=list(csv.DictReader(open(os.path.join(HERE,"data","e17_tools.csv"))))
    c=collections.defaultdict(lambda:[0,0])
    for r in rows:
        k=("ET" if "extended" in r["model"] else "3.8", r["mode"])
        c[k][1]+=1; c[k][0]+=int(r["answer_ok"])
    print("\n=== E2: 回答到達率 + Fisher/Wilson ===")
    for mode in ("blocking","nb_silent","nb_progress"):
        e,en=c[("ET",mode)]; t,tn=c[("3.8",mode)]
        lo,hi=wilson(e,en)
        p=fisher_exact(e,en-e,t,tn-t)
        print("  %-12s ET %2d/%2d [95%%CI %.0f-%.0f%%]  3.8-live %2d/%2d  Fisher p=%.2e"
              % (mode,e,en,100*lo,100*hi,t,tn,p))

if __name__=="__main__":
    main(); e1(); mechanism(); rates()

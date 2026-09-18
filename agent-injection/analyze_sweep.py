#!/usr/bin/env python3
"""本測定の集計。プロンプト単位と試行単位の両方、能力天井を分母として併記する。"""
import csv,collections,json,math,sys

def wilson(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    p=k/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (max(0.0,c-h)*100, min(1.0,c+h)*100)

rows=[r for r in csv.DictReader(open(sys.argv[1] if len(sys.argv)>1 else 'out_sweep.csv'))]
ceil={r['model']:0 for r in csv.DictReader(open('out_ceiling.csv'))}
cn=collections.Counter()
for r in csv.DictReader(open('out_ceiling.csv')):
    cn[r['model']]+=1
    if r['sink']=='1': ceil[r['model']]+=1

print(f"総試行: {len(rows)}\n")
print("=== 攻撃: モデル別(試行単位 / プロンプト単位 / 能力天井) ===")
print(f"{'model':24} {'試行':>10} {'sink率':>18} {'発火本数':>9} {'parse失敗':>9} {'能力天井':>8}")
for m in sorted(set(r['model'] for r in rows)):
    sub=[r for r in rows if r['model']==m and r['kind']=='attack']
    if not sub: continue
    n=len(sub); k=sum(int(r['sink']) for r in sub)
    lo,hi=wilson(k,n)
    per=collections.defaultdict(int)
    for r in sub:
        if r['sink']=='1': per[r['id']]+=1
    pe=sum(int(r['parse_error']) for r in sub)
    print(f"{m:24} {k:4}/{n:<5} [{lo:5.1f},{hi:5.1f}]% {len(per):5}/12 {pe:9} {ceil.get(m,0):6}/{cn.get(m,0)}")
print()
print("=== 良性(誤作動の対照) ===")
for m in sorted(set(r['model'] for r in rows)):
    sub=[r for r in rows if r['model']==m and r['kind']=='benign']
    if not sub: continue
    n=len(sub)
    print(f"  {m:24} sink {sum(int(r['sink']) for r in sub):2}/{n:<3} ツール選択 {sum(int(r['ii_tool']) for r in sub):2}/{n:<3} parse失敗 {sum(int(r['parse_error']) for r in sub):2}/{n}")
print()
print("=== 発火したプロンプトID(モデル別) ===")
for m in sorted(set(r['model'] for r in rows)):
    ids=sorted({r['id'] for r in rows if r['model']==m and r['sink']=='1'})
    if ids: print(f"  {m:24} {ids}")
print()
print("=== 同一入力の非決定性(thinking の有無で見る) ===")
print(f"{'model':24} {'thoughts中央値':>14} {'同一id内で結果が割れた本数':>26}")
for m in sorted(set(r['model'] for r in rows)):
    sub=[r for r in rows if r['model']==m and r['kind']=='attack']
    if not sub: continue
    th=[int(r['thoughts']) for r in sub if r['thoughts'] not in ('','None')]
    split=0
    for i in {r['id'] for r in sub}:
        v={r['sink'] for r in sub if r['id']==i}
        if len(v)>1: split+=1
    med=__import__('statistics').median(th) if th else 0
    print(f"{m:24} {med:14} {split:26}")

"""記事に載せる判定を1か所に集約する(読者が検算できるように)。"""
import re, csv, collections, os

# 難問で「前置き」から入ったか: 最初の発話の先頭20字にこのいずれかを含む
PREAMBLE = re.compile(r"(お待ち|考え|計算し|確認し|少々|ちょっと|かしこまり|承知|少し|そうですね|えーと|うーん)")
# 音声として不適切な出力: LaTeX or Markdown箇条書き or 強調
NOT_SPEECH = re.compile(r"(\$|\\frac|\\\(|\n\n\d+\.\s|\n- |\*\*)")

def nm(r):
    m=r["model"].replace("gemini-","").replace("-flash-native-audio-latest","-native").replace("-flash-live-preview","-flash")
    return m+((" "+r["level"]) if r["level"] else "")

if __name__=="__main__":
    rows=list(csv.DictReader(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"data","e16_thinking.csv"))))
    print("=== 難問の前置き率（分母は音声が返った試行 ok=1）===")
    c=collections.defaultdict(lambda:[0,0])
    for r in rows:
        if r["difficulty"]!="hard" or r["ok"]!="1": continue
        k=nm(r); c[k][1]+=1
        if PREAMBLE.search((r.get("first_say") or "")[:20]): c[k][0]+=1
    et=[0,0]; non=[0,0]
    for k in sorted(c):
        n,t=c[k]; print("  %-34s %2d/%2d (%3.0f%%)"%(k,n,t,100*n/t))
        (et if "extended" in k else non)[0]+=n; (et if "extended" in k else non)[1]+=t
    print("  ET計 %d/%d  非ET計 %d/%d"%(et[0],et[1],non[0],non[1]))
    print("\n=== 音声として不適切な出力を含む試行（全36試行中）===")
    d=collections.defaultdict(lambda:[0,0])
    for r in rows:
        k=nm(r); d[k][1]+=1
        if NOT_SPEECH.search(r.get("said") or ""): d[k][0]+=1
    for k in sorted(d):
        n,t=d[k]; print("  %-34s %2d/%2d"%(k,n,t))

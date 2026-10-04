"""第3部(参考デモ方式)の試走の集計。usage: python3 bench/demo_summary.py > data/DEMO_REPORT.md"""
import json, os, collections, statistics as S
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = [("demo_rules_search", "ルールだけ(モデルなし・探索のおすすめに従う)"), ("demo_kev_rules", "kev-4b・参考デモ方式(長い JSON＋ルール＋質問3つ)"),
        ("demo_kev_labeled", "kev-4b・選択肢に判定(最初の版。目的の文が右へ引っ張った可能性)"), ("demo_laya_labeled", "laya-ml・選択肢に判定(最初の版。入力が切り捨てられた)"),
        ("demo_kev_labeled2", "kev-4b・選択肢に判定(作り直した版)"), ("demo_kev_labeled2_goal", "kev-4b・作り直した版＋「おすすめが無ければ右へ進む SAFE を優先(ゴールは右)」"), ("demo_laya_labeled2", "laya-ml・選択肢に判定(作り直した版)"),
        ("demo_rules_labeled2", "ルールだけ・選択肢の判定どおり(モデルなし。SAFE のおすすめ、なければ並び順で最初の SAFE)"),
        ("demo_rules_labeled2_right", "同上、ただし SAFE を右へ進む操作から順に探す")]
print("# 第3部の集計(bench/demo_summary.py)\n")
print("| TAG | 条件 | 回数 | 死亡 | 時間切れ | 足場 | 向こう岸 | 右端 | 最高 x | 遅れ p50 | モデル p50(ms) | 判断数 | 選んだ選択肢の判定が SAFE | 探索のおすすめに従った | 選択の上位 |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for t, name in RUNS:
    p = os.path.join(ROOT, "data", "play", t, "episodes.jsonl")
    if not os.path.exists(p): continue
    eps = [json.loads(l) for l in open(p)]; ds = [d for e in eps for d in e["decisionsLog"]]
    DEATH = {"pit", "spikes", "press"}
    safe = sum(1 for d in ds if d["state"]["landing"]["if_chosen_now"][d["a"]]["surface"] not in DEATH and not d["state"]["landing"]["if_chosen_now"][d["a"]].get("triggers_spike_floor"))
    rec = [d for d in ds if (d["state"].get("search") or {}).get("recommended_first_action")]
    same = sum(1 for d in rec if d["state"]["search"]["recommended_first_action"] == d["a"])
    oc = collections.Counter(e["outcome"] for e in eps)
    print(f"| {t} | {name} | {len(eps)} | {oc['died']} | {oc['timeout']} | {sum(e['platform'] for e in eps)} | {sum(e['crossed'] for e in eps)} | {oc['right_edge']} | {max(e['maxX'] for e in eps)} | "
          f"{S.median(d['lagFrames'] for d in ds)} | {S.median(d['modelMs'] for d in ds)} | {len(ds)} | {safe} | {same}/{len(rec)} | {collections.Counter(d['a'] for d in ds).most_common(3)} |")
print("\n注: SAFE の数え方 = 選んだ操作に付いていた予測が穴・トゲ・板・罠の作動でないもの(予測の当たり外れは問わない)")

# 判定とおすすめの内訳(記事の第3部の数字の出典)
print("\n## 判定とおすすめの内訳\n")
print("| TAG | SAFE の選択肢があった判断 | そのうち SAFE を選んだ | おすすめあり | おすすめに DEATH が付いていた | おすすめが SAFE | おすすめが SAFE のとき従った | DEATH の付いたおすすめに従った | その場でジャンプ(うち空中) |")
print("|---|---|---|---|---|---|---|---|---|")
DEATH = {"pit", "spikes", "press"}
bad = lambda L, a: L[a]["surface"] in DEATH or L[a].get("triggers_spike_floor")
allb = []
for t, name in RUNS:
    p = os.path.join(ROOT, "data", "play", t, "episodes.jsonl")
    if not os.path.exists(p): continue
    ds = [d for l in open(p) for d in json.loads(l)["decisionsLog"]]
    allb += [d["buildMs"] for d in ds if d.get("buildMs") is not None]
    L = lambda d: d["state"]["landing"]["if_chosen_now"]
    hs = [d for d in ds if any(not bad(L(d), a) for a in L(d))]
    rec = [d for d in ds if (d["state"].get("search") or {}).get("recommended_first_action")]
    R = lambda d: d["state"]["search"]["recommended_first_action"]
    rd = [d for d in rec if bad(L(d), R(d))]; rs = [d for d in rec if not bad(L(d), R(d))]
    jp = [d for d in ds if d["a"] == "jump"]
    print(f"| {t} | {len(hs)} | {sum(not bad(L(d), d['a']) for d in hs)} | {len(rec)} | {len(rd)} | {len(rs)} | {sum(R(d) == d['a'] for d in rs)} | {sum(R(d) == d['a'] for d in rd)} | {len(jp)}({sum(not d['state']['player']['grounded'] for d in jp)}) |")
allb.sort()
print(f"\n予測と探索の時間(全条件の判断 {len(allb)} 件の buildMs): p50 {S.median(allb):.1f}ms / p90 {allb[int(len(allb) * 0.9)]:.1f}ms / 最大 {allb[-1]:.1f}ms")

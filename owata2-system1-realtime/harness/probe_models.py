"""崖際の同じ場面(16通り: 足場の位置4×向き2×崖までの距離2)で、状態の文章だけ変えて確率を比べる。ゲームは動かさない。
条件: G0F0 = 試走 rt2〜rt11 の文章(目的「右へ進むこと、死なないこと」、向こう岸なし) / G1F1 = rt12〜rt14 の文章(目的「右端まで進んで次のステージへ」＋向こう岸)。
向きの効果: 「足場が左へ動いている」と「右へ動いている」で、1位が左系(left/leftjump_*)になる割合を比べる。
usage: python3 harness/probe_models.py → data/probe_models.json"""
import json, urllib.request, statistics as S, collections, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = {"laya-ml": "http://127.0.0.1:8078/v1/systemone", "kev-4b": "http://127.0.0.1:8009/v1/systemone"}
ACTS = ["right", "left", "wait", "jump_big", "rightjump_big", "leftjump_big", "jump_small", "rightjump_small", "leftjump_small", "attack", "pose"]
LAB = {"right": "右へ歩く(空中でも右へ動く)", "left": "左へ歩く(空中でも左へ動く)", "wait": "何もしない", "jump_big": "その場でジャンプ",
       "rightjump_big": "右へジャンプ", "leftjump_big": "左へジャンプ", "jump_small": "その場で小ジャンプ(ボタンを短く押す・低い)",
       "rightjump_small": "右へ小ジャンプ(ボタンを短く押す・低い)", "leftjump_small": "左へ小ジャンプ(ボタンを短く押す・低い)",
       "attack": "攻撃(前に弾を撃つ)", "pose": "ポーズを取る"}
GOAL = {"G0": "目的: 右へ進むこと、死なないこと。", "G1": "目的: 画面の右端まで進んで、次のステージへ行くこと。"}
FAR = {"F0": "", "F1": "その先、右へ 210px の所から地面がまた続いている。"}
def state(g, f, x0, mv, edge):
    return (f"横スクロールのアクションゲーム。あなたは自機を操作する。{GOAL[g]}\n自機: x=176, y=302(y が小さいほど上)。"
            f"足元の地面は右へ {edge}px で途切れる(その先にトゲがある)。{FAR[f]}\n宙に浮いた足場が x={x0}〜{x0 + 55}、y=245 にある({mv}へ動いている)。")
def ask(url, st):
    body = {"state": st, "model": "latest", "questions": {"move": {"type": "choice", "instructions": "次の操作(約0.1秒)を1つ選ぶ。",
            "criteria": {"ABCDEFGHIJK"[i]: LAB[a] for i, a in enumerate(ACTS)}}}}
    r = json.loads(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), {"content-type": "application/json"}), timeout=60).read())
    node = (r.get("answers") or {}).get("values", {}).get("move") or (r.get("answers") or {}).get("move")
    p = node["probabilities"]; return {a: p.get("ABCDEFGHIJK"[i], 0) for i, a in enumerate(ACTS)}
out = {}
for m, url in MODELS.items():
    for g, f in (("G0", "F0"), ("G1", "F1")):
        res = []
        for x0 in (200, 240, 280, 320):
            for mv in ("右", "左"):
                for edge in (4, 12):
                    p = ask(url, state(g, f, x0, mv, edge)); res.append((mv, p))
        top = lambda p: max(p, key=p.get)
        leftish = lambda a: a.startswith("left")
        out[f"{m}/{g}{f}"] = {
            "右へジャンプの確率 平均": round(S.mean(p["rightjump_big"] for _, p in res), 3),
            "1位の内訳": dict(collections.Counter(top(p) for _, p in res).most_common()),
            "足場が右へ動く場面で1位が左系": f"{sum(leftish(top(p)) for mv, p in res if mv == '右')}/8",
            "足場が左へ動く場面で1位が左系": f"{sum(leftish(top(p)) for mv, p in res if mv == '左')}/8"}
        print(m, g + f, out[f"{m}/{g}{f}"], flush=True)
json.dump(out, open(os.path.join(ROOT, "data", "probe_models.json"), "w"), ensure_ascii=False, indent=1)

"""probe_models.py の追加(外部レビュー対応)。崖際の16場面で:
(1) 呼び方と並び順を分ける: v2の呼び方×v2の並び / v3の呼び方×v2の並び / v2の呼び方×v3の並び / v3×v3 で「右へ大ジャンプ」の確率
(2) 単語の効果: 足場の向きを「左へ/右へ動いている」と書く版と、「x が減る/増える向きに動いている」(左右の語を使わない)版で、1位が左系になる割合
usage: python3 harness/probe_models2.py → data/probe_models2.json"""
import json, urllib.request, statistics as S, collections, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = {"laya-ml": "http://127.0.0.1:8078/v1/systemone", "kev-4b": "http://127.0.0.1:8009/v1/systemone"}
A2 = ["right", "left", "wait", "jump_small", "rightjump_small", "leftjump_small", "jump_big", "rightjump_big", "leftjump_big", "attack", "pose"]
A3 = ["right", "left", "wait", "jump_big", "rightjump_big", "leftjump_big", "jump_small", "rightjump_small", "leftjump_small", "attack", "pose"]
L2 = {"right": "右へ歩く(空中でも右へ動く)", "left": "左へ歩く(空中でも左へ動く)", "wait": "何もしない",
      "jump_small": "その場で小ジャンプ(低い)", "rightjump_small": "右へ小ジャンプ(低い)", "leftjump_small": "左へ小ジャンプ(低い)",
      "jump_big": "その場で大ジャンプ(高い)", "rightjump_big": "右へ大ジャンプ(高い)", "leftjump_big": "左へ大ジャンプ(高い)",
      "attack": "攻撃(前に弾を撃つ)", "pose": "ポーズを取る"}
L3 = {**L2, "jump_big": "その場でジャンプ", "rightjump_big": "右へジャンプ", "leftjump_big": "左へジャンプ",
      "jump_small": "その場で小ジャンプ(ボタンを短く押す・低い)", "rightjump_small": "右へ小ジャンプ(ボタンを短く押す・低い)", "leftjump_small": "左へ小ジャンプ(ボタンを短く押す・低い)"}
def state(x0, mv, edge, words=True):
    d = {"右": "右へ動いている", "左": "左へ動いている"} if words else {"右": "x が増える向きに動いている", "左": "x が減る向きに動いている"}
    return (f"横スクロールのアクションゲーム。あなたは自機を操作する。目的: 右へ進むこと、死なないこと。\n自機: x=176, y=302(y が小さいほど上)。"
            f"足元の地面は右へ {edge}px で途切れる(その先にトゲがある)。\n宙に浮いた足場が x={x0}〜{x0 + 55}、y=245 にある({d[mv]})。")
def ask(url, st, acts, lab):
    body = {"state": st, "model": "latest", "questions": {"move": {"type": "choice", "instructions": "次の操作(約0.1秒)を1つ選ぶ。",
            "criteria": {"ABCDEFGHIJK"[i]: lab[a] for i, a in enumerate(acts)}}}}
    r = json.loads(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), {"content-type": "application/json"}), timeout=60).read())
    node = (r.get("answers") or {}).get("values", {}).get("move") or (r.get("answers") or {}).get("move")
    p = node["probabilities"]; return {a: p.get("ABCDEFGHIJK"[i], 0) for i, a in enumerate(acts)}
scenes = [(x0, mv, e) for x0 in (200, 240, 280, 320) for mv in ("右", "左") for e in (4, 12)]
out = {}
for m, url in MODELS.items():
    for nm, acts, lab in (("呼び方v2×並びv2", A2, L2), ("呼び方v3×並びv2", A2, L3), ("呼び方v2×並びv3", A3, L2), ("呼び方v3×並びv3", A3, L3)):
        ps = [ask(url, state(*s), acts, lab) for s in scenes]
        out[f"{m}/{nm}"] = {"右へ大ジャンプの確率 平均": round(S.mean(p["rightjump_big"] for p in ps), 3),
                            "その場で大ジャンプの確率 平均": round(S.mean(p["jump_big"] for p in ps), 3),
                            "1位の内訳": dict(collections.Counter(max(p, key=p.get) for p in ps).most_common(3))}
        print(m, nm, out[f"{m}/{nm}"], flush=True)
    for words in (True, False):
        res = [(s[1], ask(url, state(*s, words=words), A3, L3)) for s in scenes]
        top = lambda p: max(p, key=p.get)
        k = f"{m}/向きの書き方={'左へ・右へ' if words else 'xが減る・増える'}"
        out[k] = {"「左」相当の場面で1位が左系": f"{sum(top(p).startswith('left') for mv, p in res if mv == '左')}/8",
                  "「右」相当の場面で1位が左系": f"{sum(top(p).startswith('left') for mv, p in res if mv == '右')}/8",
                  "1位の内訳": dict(collections.Counter(top(p) for _, p in res).most_common(3))}
        print(k, out[k], flush=True)
json.dump(out, open(os.path.join(ROOT, "data", "probe_models2.json"), "w"), ensure_ascii=False, indent=1)

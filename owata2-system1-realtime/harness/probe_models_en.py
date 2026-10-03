"""probe_models.py / probe_models2.py の英語版(外部レビュー: kev-4b のモデルカードは Languages: English)。
崖際16場面で、目的の書き方(G0/G1＋向こう岸)と、足場の向きの書き方(left/right と x decreasing/increasing)を比べる。
usage: python3 harness/probe_models_en.py → data/probe_models_en.json"""
import json, urllib.request, statistics as S, collections, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = {"laya-ml": "http://127.0.0.1:8078/v1/systemone", "kev-4b": "http://127.0.0.1:8009/v1/systemone"}
ACTS = ["right", "left", "wait", "jump_big", "rightjump_big", "leftjump_big", "jump_small", "rightjump_small", "leftjump_small", "attack", "pose"]
LAB = {"right": "walk right (also moves right in the air)", "left": "walk left (also moves left in the air)", "wait": "do nothing",
       "jump_big": "jump in place", "rightjump_big": "jump to the right", "leftjump_big": "jump to the left",
       "jump_small": "small hop in place (tap the button, low)", "rightjump_small": "small hop to the right (tap the button, low)",
       "leftjump_small": "small hop to the left (tap the button, low)", "attack": "attack (shoot a bullet forward)", "pose": "strike a pose"}
GOAL = {"G0": "Goal: move right and do not die.", "G1": "Goal: reach the right edge of the screen and go on to the next stage."}
FAR = {"F0": "", "F1": " Beyond that, the ground continues again 210px to the right."}
def state(g, f, x0, mv, edge, words=True):
    d = {"R": "moving right", "L": "moving left"} if words else {"R": "moving in the direction of increasing x", "L": "moving in the direction of decreasing x"}
    return (f"Side-scrolling action game. You control the character. {GOAL[g]}\nYou: x=176, y=302 (smaller y is higher). "
            f"The ground under you ends {edge}px to the right, with spikes beyond it.{FAR[f]}\nA floating platform is at x={x0}-{x0 + 55}, y=245, {d[mv]}.")
def ask(url, st):
    body = {"state": st, "model": "latest", "questions": {"move": {"type": "choice", "instructions": "Choose the next action (about 0.1 s).",
            "criteria": {"ABCDEFGHIJK"[i]: LAB[a] for i, a in enumerate(ACTS)}}}}
    r = json.loads(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), {"content-type": "application/json"}), timeout=60).read())
    node = (r.get("answers") or {}).get("values", {}).get("move") or (r.get("answers") or {}).get("move")
    p = node["probabilities"]; return {a: p.get("ABCDEFGHIJK"[i], 0) for i, a in enumerate(ACTS)}
scenes = [(x0, mv, e) for x0 in (200, 240, 280, 320) for mv in ("R", "L") for e in (4, 12)]
top = lambda p: max(p, key=p.get)
out = {}
for m, url in MODELS.items():
    for g, f, words in (("G0", "F0", True), ("G1", "F1", True), ("G0", "F0", False)):
        res = [(s[1], ask(url, state(g, f, *s, words=words))) for s in scenes]
        k = f"{m}/{g}{f}/{'left・right' if words else 'x decreasing・increasing'}"
        out[k] = {"jump to the right の確率 平均": round(S.mean(p["rightjump_big"] for _, p in res), 3),
                  "1位の内訳": dict(collections.Counter(top(p) for _, p in res).most_common(3)),
                  "左向きの場面で1位が左系": f"{sum(top(p).startswith('left') for mv, p in res if mv == 'L')}/8",
                  "右向きの場面で1位が左系": f"{sum(top(p).startswith('left') for mv, p in res if mv == 'R')}/8"}
        print(k, out[k], flush=True)
json.dump(out, open(os.path.join(ROOT, "data", "probe_models_en.json"), "w"), ensure_ascii=False, indent=1)

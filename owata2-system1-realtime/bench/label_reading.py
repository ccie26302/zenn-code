"""モデルが選択肢の SAFE / DEATH の判定を読めるか(ゲームは動かさない)。
(1) 単純な3択(DEATH/SAFE/DEATH と、SAFE を先頭に入れ替えたもの、判定なしの文章だけのもの)
(2) 試走で出た場面(demo_kev_labeled と demo_laya_labeled の各回の先頭6判断、6回ぶん)で、作り直した版の入力を作り、選択肢の並びをそのままと逆順の2通りで
usage: python3 bench/label_reading.py → data/label_reading.json(laya-ml を :8078、kev-4b を :8009 で起動しておく)"""
import json, os, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = {"kev-4b": 8009, "laya-ml": 8078}
def ask(port, state, ins, crit):
    body = {"state": state, "model": "latest", "questions": {"q": {"type": "choice", "instructions": ins, "criteria": crit}}}
    r = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/v1/systemone", json.dumps(body).encode(), {"content-type": "application/json"}), timeout=60).read())
    A = r.get("answers", {}); A = A.get("values", A); return A["q"]["probabilities"]
out = {"simple": [], "game": {}}
SIMPLE = [("Each option is marked SAFE or DEATH by a reliable simulator.", "Choose an option that is SAFE. Never choose DEATH.", {"A": "DEATH: walk right", "B": "SAFE: do nothing", "C": "DEATH: jump right"}, "B"),
          ("Each option is marked SAFE or DEATH by a reliable simulator.", "Choose an option that is SAFE. Never choose DEATH.", {"A": "SAFE: walk right", "B": "DEATH: do nothing", "C": "DEATH: jump right"}, "A"),
          ("A game character stands at the edge of a cliff. Walking right or jumping right now falls into a spike pit and dies. Doing nothing is safe.", "Which action should the character take?", {"A": "walk right", "B": "do nothing", "C": "jump right"}, "B")]
for st, ins, crit, safe in SIMPLE:
    row = {"criteria": crit, "safe": safe}
    for m, port in MODELS.items(): p = ask(port, st, ins, crit); row[m] = {"p_safe": round(p[safe], 3), "top": max(p, key=p.get)}
    out["simple"].append(row); print(row)
NAME = {"noop": "do nothing", "right": "walk right", "right_jump": "jump right", "jump": "jump in place", "left": "walk left", "left_jump": "jump left"}
SAY = {"platform": ("SAFE", "lands on the moving platform"), "far_ground": ("SAFE", "lands on the far ground"), "press_top": ("SAFE", "lands on top of the press"), "near_ground": ("SAFE", "lands back on the near ground"),
       "pit": ("DEATH", "falls into the spike pit"), "spikes": ("DEATH", "hits the rising spikes"), "press": ("DEATH", "is crushed by the press"), "stays_on_near_ground": ("SAFE", "stays on the near ground"),
       "stays_on_far_ground": ("SAFE", "stays on the far ground"), "stays_on_platform": ("SAFE", "stays on the platform"), "stays_on_press_top": ("SAFE", "stays on the press"), "airborne": ("UNKNOWN", "still in the air")}
STATE = "A side-scrolling game. Each option below was checked by a physics simulator that already accounts for the reaction delay, and is marked SAFE or DEATH."
INS = "Choose an option marked SAFE. Never choose DEATH. Among SAFE options, prefer RECOMMENDED."
scenes = []
for t in ("demo_kev_labeled", "demo_laya_labeled"):
    for e in [json.loads(l) for l in open(os.path.join(ROOT, "data", "play", t, "episodes.jsonl"))][:6]:
        for d in e["decisionsLog"][:6]: scenes.append(d)
for order in ("as_is", "reversed"):
    res = {m: [0, 0] for m in MODELS}
    for d in scenes:
        L = d["state"]["landing"]["if_chosen_now"]; rec = (d["state"].get("search") or {}).get("recommended_first_action")
        crit = {}
        for a in L:
            tag, txt = SAY.get(L[a]["surface"], ("UNKNOWN", L[a]["surface"]))
            if L[a].get("triggers_spike_floor"): tag, txt = "DEATH", "lands on the platform and triggers the rising spikes"
            crit[a] = f"{tag}{' (RECOMMENDED)' if a == rec else ''}: {NAME[a]}, {txt}"
        if not any(v.startswith("SAFE") for v in crit.values()): continue
        if order == "reversed": crit = dict(reversed(list(crit.items())))
        for m, port in MODELS.items():
            p = ask(port, STATE, INS, crit); top = max(p, key=p.get); res[m][1] += 1; res[m][0] += crit[top].startswith("SAFE")
    out["game"][order] = {m: f"{v[0]}/{v[1]}" for m, v in res.items()}; print(order, out["game"][order])
json.dump(out, open(os.path.join(ROOT, "data", "label_reading.json"), "w"), ensure_ascii=False, indent=1)

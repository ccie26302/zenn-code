"""足場の速さ(px/コマ)。最終比較の状態文から、自機が動かない行動(wait/attack/pose、接地)の前後で足場の x0 がどれだけ動いたかを、
その間のコマ数(その判断の遅れ＋行動のコマ数＋1)で割る。向きが変わった区間は除く。usage: python3 bench/platform_speed.py"""
import json, re, glob, statistics as S, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOTAL = {"right": 6, "left": 6, "wait": 6, "jump_small": 6, "rightjump_small": 6, "leftjump_small": 6, "jump_big": 16, "rightjump_big": 16, "leftjump_big": 16, "attack": 6, "pose": 6}
rx = re.compile(r"platform is at x=(-?\d+)-(-?\d+), y=\d+, moving (left|right)")
v = []
for f in glob.glob(os.path.join(ROOT, "data/play/fin_*_en_[123]/episodes.jsonl")):
    for l in open(f):
        tr = json.loads(l)["traj"]
        for a, b in zip(tr, tr[1:]):
            if a["a"] not in ("wait", "attack", "pose") or ",g," not in a["k"] or a["x"] != b["x"]: continue
            ma, mb = rx.search(a.get("st") or ""), rx.search(b.get("st") or "")
            if not (ma and mb) or ma.group(3) != mb.group(3): continue
            frames = a["lagFrames"] + TOTAL[a["a"]] + 1
            v.append(abs(int(mb.group(1)) - int(ma.group(1))) / frames)
out = {"区間の数": len(v), "px/コマ 中央値": round(S.median(v), 2), "四分位": [round(sorted(v)[len(v) // 4], 2), round(sorted(v)[3 * len(v) // 4], 2)]}
json.dump(out, open(os.path.join(ROOT, "data/platform_speed.json"), "w"), ensure_ascii=False, indent=1); print(out)

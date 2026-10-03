"""目の精度。(1) 自機: 目視ラベル186コマ(1面・1名)を今の判定(形の照合 thr=0.43)で。(2) トゲの列: 録画 rt5/rt6 を7コマおきに。
usage: uv run --with numpy --with scipy --with pillow python bench/eye_validate.py  → data/eye_validation.json"""
import sys, os, json, glob, collections, numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "perception"))
from match import detect, detect_spikes
arr = lambda f: np.asarray(Image.open(f).convert("RGB")).astype(np.int32).sum(axis=2)
L = json.load(open(os.path.join(ROOT, "data/m1/labels_v3.json")))["labels"]
conf = collections.Counter(); scores = collections.defaultdict(list)
for i, lab in L.items():
    d = detect(arr(os.path.join(ROOT, f"data/m1/frames/f{int(i):04d}.png")))
    conf[(lab, "あり" if d["player"] else "なし")] += 1; scores[lab].append(d["score"])
player = {"ラベル×判定": {f"{a}→{b}": n for (a, b), n in sorted(conf.items())},
          "score": {k: {"min": round(min(v), 3), "max": round(max(v), 3)} for k, v in scores.items()}, "閾値": 0.43,
          "注": "ラベル alive=生存 / absent=自機なし / dying=死亡演出。目視1名・1面のみ"}
rows = collections.Counter(); miss = []; N = 0
for d in sorted(glob.glob(os.path.join(ROOT, "data/play/rt5_layaml_gain_rec/rec/ep*"))) + sorted(glob.glob(os.path.join(ROOT, "data/play/rt6_layaml_v3_rec/rec/ep*"))):
    for f in sorted(glob.glob(d + "/*.png"))[::7]:
        r = detect_spikes(arr(f)); N += 1; rows[len(r)] += 1
        if len(r) != 1: miss.append(os.path.relpath(f, ROOT))
spikes = {"コマ数": N, "列の本数ごとのコマ数": dict(rows), "1本以外のコマ": miss[:20],
          "注": "1面には穴が1つ。0本のコマはすべて樹海側でトゲが画面外か目視で確認する(確認結果は記事に記載)"}
json.dump({"自機": player, "トゲの列": spikes}, open(os.path.join(ROOT, "data/eye_validation.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({"自機": player, "トゲ": {k: v for k, v in spikes.items() if k != "1本以外のコマ"}}, ensure_ascii=False))

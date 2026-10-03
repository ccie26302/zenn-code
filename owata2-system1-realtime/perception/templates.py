"""自機のお手本(テンプレート)を作る。M1 のラベル付き生存コマ(スクロールなし)から、
背景差分で取れた自機の画素だけを切り出し、外形の大きさで姿勢ごとにまとめる。"""
import json, os, numpy as np
from PIL import Image
D = os.path.join(os.path.dirname(__file__), "..", "data", "m1")
meta = json.load(open(os.path.join(D, "pred.json"))); lab = json.load(open(os.path.join(D, "labels_v3.json")))["labels"]
bg = np.asarray(Image.open(os.path.join(D, "bg.png")).convert("RGB")).astype(int).sum(axis=2)
crops = []
for m in meta:
    if lab[str(m["id"])] != "alive" or not m.get("v3"): continue
    a = np.asarray(Image.open(os.path.join(D, "frames", m["file"])).convert("RGB")).astype(int).sum(axis=2)
    b = m["v3"]["box"]; x0, x1, y0, y1 = b["x0"] - 2, b["x1"] + 3, b["y0"] - 2, b["y1"] + 3
    fg = ((a < 300) & (bg - a > 150))[y0:y1, x0:x1]
    ys, xs = np.where(fg)
    if len(xs) < 20: continue
    crops.append(fg[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
# 外形(高さ, 幅)でまとめ、各グループの代表(画素数が中央値のもの)を採用
groups = {}
for c in crops: groups.setdefault((c.shape[0] // 2, c.shape[1] // 2, int(c[:, : c.shape[1] // 2].sum() > c[:, c.shape[1] // 2 :].sum())), []).append(c)
tpls = []
for k, cs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    if len(cs) < 1: continue
    cs.sort(key=lambda c: c.sum()); tpls.append(cs[len(cs) // 2])
np.savez_compressed(os.path.join(os.path.dirname(__file__), "player_templates.npz"), *tpls)
print(f"crops={len(crops)} templates={len(tpls)} shapes={[t.shape for t in tpls]}")
for i, t in enumerate(tpls):
    Image.fromarray((~t * 255).astype(np.uint8)).resize((t.shape[1] * 4, t.shape[0] * 4), Image.NEAREST).save(os.path.join(D, f"tpl_{i}.png"))

"""「足場に乗った」を録画の全コマで数え直す(外部監査の方法)。判断の瞬間だけを見る report.py の数え方は取りこぼす(目が足場の上を「空中」と返すことがある)。
基準: 足場が見えていて、自機が y 228〜236・足場の x 範囲(±4px)に10コマ以上続けて立っている回。
注意: CPU を多く使う。試走中に回すと判断の遅れが乱れるので、試走が終わってから回す。
usage: python3 bench/landing_from_rec.py <TAG> [<TAG> ...] → data/landing_rec_<TAG>.json"""
import sys, os, glob, json, numpy as np
from multiprocessing import Pool
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "perception"))
from PIL import Image
import match as M
L = lambda p: np.asarray(Image.open(p).convert("RGB")).astype(np.int32).sum(axis=2)
M.set_platform_template(L(os.path.join(ROOT, "data/m1/bg.png")))
def work(arg):
    tag, ep = arg; d = os.path.join(ROOT, f"data/play/{tag}/rec/ep{ep}")
    if not os.path.isdir(d): return (ep, None)
    run = best = 0
    for f in sorted(glob.glob(d + "/*.png")):
        s = L(f); pl = M.detect_platform(s)
        if not pl: run = 0; continue
        p = M.detect(s)["player"]
        if p and 228 <= p["y"] <= 236 and pl["x0"] - 4 <= p["x"] <= pl["x1"] + 4: run += 1; best = max(best, run)
        else: run = 0
    return (ep, best)
if __name__ == "__main__":
    for tag in sys.argv[1:]:
        eps = [json.loads(l) for l in open(os.path.join(ROOT, f"data/play/{tag}/episodes.jsonl"))]
        jobs = [(tag, e["ep"]) for e in eps if any(x["x"] >= 190 for x in e["traj"]) or e["maxX"] >= 200]
        with Pool(12) as P: res = dict(P.map(work, jobs, chunksize=2))
        out = {"tag": tag, "基準": "足場の上に10コマ以上連続(y 228〜236)", "対象の回": len(jobs),
               "足場に乗った回": sorted(ep for ep, b in res.items() if b and b >= 10), "最長コマ数": res}
        json.dump(out, open(os.path.join(ROOT, f"data/landing_rec_{tag}.json"), "w"), ensure_ascii=False, indent=1)
        print(tag, "足場に乗った回", len(out["足場に乗った回"]), flush=True)

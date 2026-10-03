"""「死亡」と数えた回を録画で確かめる。目は自機を2回続けて見失うと死亡と判定するが、S のポーズ中は自機の形が変わって見失うことがある。
各回の録画の最後(回の終了後に撮った約40コマ)で、自機のお手本が閾値以上で見つかれば、実際は生きていた(誤判定)とみなす。
usage: python3 bench/death_check.py <TAG> [...] → data/death_check_<TAG>.json"""
import sys, os, glob, json, numpy as np
from multiprocessing import Pool
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "perception"))
from PIL import Image
import match as M
L = lambda p: np.asarray(Image.open(p).convert("RGB")).astype(np.int32).sum(axis=2)
def work(arg):
    tag, ep = arg; d = os.path.join(ROOT, f"data/play/{tag}/rec/ep{ep}")
    if not os.path.isdir(d): return (ep, None)
    meta = json.load(open(os.path.join(d, "meta.json")))
    end = [m["i"] for m in meta if m["action"] == "end"]
    seen = sum(1 for i in end[-20:] if M.detect(L(os.path.join(d, f"{i:05d}.png")))["player"])
    return (ep, seen)
if __name__ == "__main__":
    for tag in sys.argv[1:]:
        eps = [json.loads(l) for l in open(os.path.join(ROOT, f"data/play/{tag}/episodes.jsonl"))]
        died = [e for e in eps if e["died"]]
        with Pool(12) as P: res = dict(P.map(work, [(tag, e["ep"]) for e in died]))
        alive = sorted(ep for ep, s in res.items() if s and s >= 10)   # 最後の20コマのうち10コマ以上で自機が見つかる
        lastpose = sorted(e["ep"] for e in died if e["traj"] and e["traj"][-1]["a"] == "pose")
        out = {"tag": tag, "死亡と数えた回": len(died), "録画なし": sum(1 for v in res.values() if v is None),
               "録画で生存(誤判定)": alive, "最後の手がポーズ": lastpose, "誤判定のうち最後がポーズ": sorted(set(alive) & set(lastpose))}
        json.dump(out, open(os.path.join(ROOT, f"data/death_check_{tag}.json"), "w"), ensure_ascii=False, indent=1)
        print(tag, "死亡", len(died), "録画で生存", len(alive), "最後がポーズ", len(lastpose), "重なり", len(out["誤判定のうち最後がポーズ"]), "録画なし", out["録画なし"], flush=True)

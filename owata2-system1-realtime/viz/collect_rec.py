"""試走中に録画したコマ(data/play/<TAG>/rec/ep<N>/)を data/video/frames と meta.json に並べる。usage: CLIPS="rt5:44,rt5:92" python3 viz/collect_rec.py"""
import json, os, shutil
B = os.path.join(os.path.dirname(__file__), "..", "data")
V = os.path.join(B, "video"); F = os.path.join(V, "frames")
shutil.rmtree(F, ignore_errors=True); os.makedirs(F)
meta, n = [], 0
for c in os.environ["CLIPS"].split(","):
    tag, ep = c.split(":"); d = os.path.join(B, "play", tag, "rec", f"ep{ep}")
    for m in json.load(open(os.path.join(d, "meta.json"))):
        os.link(os.path.join(d, f"{m['i']:05d}.png"), os.path.join(F, f"{n:05d}.png")); meta.append({**m, "n": n}); n += 1
json.dump(meta, open(os.path.join(V, "meta.json"), "w")); print("frames", n)

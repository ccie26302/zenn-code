"""目のサーバ(AI なしのルール特徴)。ハーネス(JS)から PNG を受けて、自機・R:Retry・カメラのずれを返す。
usage: uv run --with numpy --with scipy --with pillow --with fastapi --with uvicorn perception/server.py [port]"""
import io, sys, numpy as np, uvicorn
from fastapi import FastAPI, Request
from PIL import Image
from match import detect, camera_shift, set_platform_template, detect_platform, ground_ahead, detect_spikes, detect_press
app = FastAPI(); STATE = {"prev": None, "prev_box": None, "cam_x": 0, "cam_y": 0, "prev_plat": None, "prev_spk": None, "prev_prs": None}
import os
_bg = os.path.join(os.path.dirname(__file__), "..", "data", "m1", "bg.png")
if os.path.exists(_bg): set_platform_template(np.asarray(Image.open(_bg).convert("RGB")).astype(np.int32).sum(axis=2))

def to_sum(png: bytes):
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGB")).astype(np.int32).sum(axis=2)

def movers(a):
    m = []
    pl = detect_platform(a)
    if pl: m.append([pl["x0"] - 6, pl["y0"] - 6, pl["x1"] + 6, pl["y0"] + 24])
    for q in detect_spikes(a):
        if q["y"] < 350: m.append([q["x0"] - 6, q["y"] - 20, q["x1"] + 6, 359])     # 上がったトゲの床と、その下の柱
    for q in detect_press(a): m.append([q["x0"] - 6, 0, q["x1"] + 6, q["y"] + 4])     # 下りてくる板と、その上の柱
    return m


@app.post("/reset")
def reset():
    STATE.update(prev=None, prev_box=None, cam_x=0, cam_y=0, prev_plat=None, prev_spk=None, prev_prs=None, prev_movers=[]); return {"ok": True}

@app.post("/perceive")
async def perceive(req: Request):
    import time; T = {}; t = time.perf_counter()
    def lap(k):
        nonlocal t; n = time.perf_counter(); T[k] = round((n - t) * 1000, 3); t = n
    a = to_sum(await req.body()); lap("decode")
    d = detect(a); p = d["player"]; lap("player")
    retry = int((a[:41, 520:] < 300).sum()) > 150
    dx = dy = 0; peak = 0.0
    if STATE["prev"] is not None:
        masks = [b for b in (STATE["prev_box"], p["box"] if p else None) if b]
        # 動く物(足場・せり上がるトゲの床と柱・下りてくる板と柱)も隠す。これらが縦に大きく動くとカメラの縦のずれと取り違える
        masks += STATE.get("prev_movers", []) + movers(a)
        dx, dy, peak = camera_shift(STATE["prev"], a, masks)
        STATE["cam_x"] -= dx; STATE["cam_y"] -= dy
    lap("camera")
    STATE["prev"] = a; STATE["prev_box"] = p["box"] if p else None; STATE["prev_movers"] = movers(a)
    world = {"x": p["x"] + STATE["cam_x"], "y": p["y"] + STATE["cam_y"]} if p else None
    plat = detect_platform(a); lap("platform")
    if plat and STATE["prev_plat"]:
        mv = plat["x0"] - STATE["prev_plat"]["x0"] + dx   # カメラのずれを除いた足場自身の動き
        plat["moving"] = "left" if mv < -1 else "right" if mv > 1 else "still"
    STATE["prev_plat"] = plat
    ground = ground_ahead(a, p); lap("ground")
    # B7: トゲの列。前回の観測からの上下の動き(世界座標で比べる。y は大きいほど下)
    spikes = detect_spikes(a)
    for sp in spikes:
        sp["wy"] = sp["y"] + STATE["cam_y"]; sp["wx0"] = sp["x0"] + STATE["cam_x"]; sp["wx1"] = sp["x1"] + STATE["cam_x"]
        prev = [q for q in (STATE["prev_spk"] or []) if min(q["wx1"], sp["wx1"]) - max(q["wx0"], sp["wx0"]) > 20]
        sp["dy"] = (sp["wy"] - min(prev, key=lambda q: abs(q["wy"] - sp["wy"]))["wy"]) if prev else None
    STATE["prev_spk"] = spikes; lap("spikes")
    press = detect_press(a)
    for q in press:
        q["wy"] = q["y"] + STATE["cam_y"]; q["wx0"] = q["x0"] + STATE["cam_x"]; q["wx1"] = q["x1"] + STATE["cam_x"]
        prev = [z for z in (STATE["prev_prs"] or []) if min(z["wx1"], q["wx1"]) - max(z["wx0"], q["wx0"]) > 20]
        q["dy"] = (q["wy"] - min(prev, key=lambda z: abs(z["wy"] - q["wy"]))["wy"]) if prev else None
    STATE["prev_prs"] = press; lap("press")
    return {"player": p, "world": world, "score": d["score"], "retry": retry, "platform": plat, "ground": ground, "spikes": spikes, "press": press, "timing_ms": T,
            "cam": {"x": STATE["cam_x"], "y": STATE["cam_y"], "dx": dx, "dy": dy, "peak": round(peak, 3)}}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8099, log_level="warning")

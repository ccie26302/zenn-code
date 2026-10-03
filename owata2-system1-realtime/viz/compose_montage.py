"""試走中に録画したコマから「注目の回を1倍速 → 全回を10倍速」の紹介動画を作る。
usage: TAG=rt8_layaml_noban_eye_rec TITLE="..." HL="21:初めて穴を越えた回,95:..." SPEED=10 OUT=x.mp4 python3 viz/compose_montage.py
録画は data/play/<TAG>/rec/ep<N>/(REC=1、全回を残すには REC_ALL=1)。"""
import json, os, subprocess
from PIL import Image, ImageDraw, ImageFont

B = os.path.join(os.path.dirname(__file__), "..", "data")
TAG = os.environ["TAG"]
P = os.path.join(B, "play", TAG)
EPS = {e["ep"]: e for e in (json.loads(l) for l in open(os.path.join(P, "episodes.jsonl")))}
# 足場に乗った回は録画で数え直した値を使う(bench/landing_from_rec.py)。無ければ判断時の値
_rl = os.path.join(B, f"landing_rec_{TAG}.json")
if os.path.exists(_rl):
    _set = set(json.load(open(_rl))["足場に乗った回"])
    for k, e in EPS.items(): e["onPlatform"] = k in _set
SPEED = int(os.environ.get("SPEED", "10"))
HL = [(int(a), b) for a, b in (h.split(":", 1) for h in os.environ.get("HL", "").split(",") if h)]
TITLE = os.environ.get("TITLE", TAG)
OUT = os.path.join(B, "video", os.environ.get("OUT", f"{TAG}_montage.mp4"))

FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
f = lambda s: ImageFont.truetype(FONT, s)
W, H, TOP = 640, 360, 150
INK, MUTED = (20, 20, 20), (110, 110, 110)
C_PLAT, C_GOAL, C_DIE, C_ALIVE = (42, 120, 214), (235, 104, 52), (175, 175, 175), (225, 225, 225)
ACT = {"jump_small": "小ジャンプ", "rightjump_small": "右へ小ジャンプ", "leftjump_small": "左へ小ジャンプ", "jump_big": "ジャンプ",
       "rightjump_big": "右へジャンプ", "leftjump_big": "左へジャンプ", "attack": "攻撃", "pose": "ポーズ", "right": "右へ歩く",
       "left": "左へ歩く", "wait": "何もしない", "start": "スタート", "end": "—", "thinking": "考え中…"}

ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H + TOP}", "-r", "60",
                       "-i", "-", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
put = lambda im, n=1: [ff.stdin.write(im.tobytes()) for _ in range(n)]

def outcome(e):
    if e.get("solved") or e.get("crossed"): return "向こう岸に着いた", C_GOAL
    if e.get("onPlatform"): return ("足場に乗った→死亡" if e["died"] else "足場に乗った"), C_PLAT
    if e.get("lost"): return "追跡を見失い打ち切り", C_ALIVE
    return ("死亡" if e["died"] else "時間切れ"), (C_DIE if e["died"] else C_ALIVE)

def card(title, sub="", sub2=""):
    im = Image.new("RGB", (W, H + TOP), "white"); d = ImageDraw.Draw(im)
    cy = (H + TOP) // 2
    d.text((W // 2, cy - 36), title, font=f(28), fill=INK, anchor="mm")
    if sub: d.text((W // 2, cy + 8), sub, font=f(17), fill=MUTED, anchor="mm")
    if sub2: d.text((W // 2, cy + 36), sub2, font=f(15), fill=MUTED, anchor="mm")
    return im

def frames(ep):
    d = os.path.join(P, "rec", f"ep{ep}")
    return d, json.load(open(os.path.join(d, "meta.json")))

def strip(d, upto, y=118):
    """全回の結果を色の帯で(左から ep0…)。今の回まで塗る"""
    n = max(EPS) + 1; w = (W - 20) / n
    for i in range(n):
        x0 = 10 + i * w
        col = outcome(EPS[i])[1] if i <= upto and i in EPS else (245, 245, 245)
        d.rectangle([x0, y, x0 + max(w - 1, 1), y + 14], fill=col)
    d.rectangle([10 + upto * w, y - 3, 10 + (upto + 1) * w - 1, y + 17], outline=INK)

def stats_upto(ep):
    s = [EPS[i] for i in sorted(EPS) if i <= ep]
    return {"best": max(e["maxX"] for e in s), "plat": sum(bool(e.get("onPlatform")) for e in s),
            "goal": sum(bool(e.get("solved") or e.get("crossed")) for e in s), "dead": sum(e["died"] for e in s)}

N = len(EPS)
allst = stats_upto(max(EPS))
_lag = sorted(t["lagFrames"] for e in EPS.values() for t in e["traj"]); LAG = _lag[len(_lag) // 2]
put(card(TITLE, f"{os.environ.get('MODEL_LABEL', 'laya-ml')}(Mac ローカル)・{N}回・リアルタイム(判断の間もゲームは進む)",
         f"画面だけを見て遊ぶ(内部状態は使わない)・考える間に進むコマ数 中央値 {LAG}コマ(実測)"), 150)

# 1) 注目の回を1倍速
for ep, cap in HL:
    e = EPS[ep]; oc, _ = outcome(e)
    put(card(cap, f"{ep + 1}回目(ep{ep})  {oc}  最大 x={e['maxX']}", "1倍速(実時間)・試走中にそのまま録画"), 100)
    d0, meta = frames(ep)
    for m in meta:
        im = Image.new("RGB", (W, H + TOP), "white"); d = ImageDraw.Draw(im)
        im.paste(Image.open(os.path.join(d0, f"{m['i']:05d}.png")).convert("RGB"), (0, TOP))
        d.line([0, TOP - 1, W, TOP - 1], fill=(190, 190, 190))
        d.text((10, 8), cap, font=f(20), fill=INK)
        d.text((10, 40), f"{ep + 1}回目  最大 x={e['maxX']}  {oc}", font=f(15), fill=MUTED)
        if m["action"] == "thinking":
            d.text((W - 10, 76), f"{m['step']}手目  考え中…({m.get('lag')}コマ、世界は動く)", font=f(18), fill=C_PLAT, anchor="ra")
        else:
            d.text((W - 10, 76), f"{m['step']}手目  {ACT.get(m['action'], m['action'])}", font=f(18), fill=(200, 40, 40), anchor="ra")
        d.text((W - 10, 128), "1倍速", font=f(13), fill=MUTED, anchor="ra")
        put(im)

# 2) 全回を SPEED 倍速
put(card(f"全{N}回を{SPEED}倍速で", "帯の色: 灰=死亡 / 薄灰=時間切れ・打ち切り / 青=足場に乗った / 橙=向こう岸に着いた",
         "上の数字はその回までの累計"), 120)
k = 0
for ep in sorted(EPS):
    d0 = os.path.join(P, "rec", f"ep{ep}")
    if not os.path.isdir(d0): continue
    meta = json.load(open(os.path.join(d0, "meta.json"))); e = EPS[ep]; oc, col = outcome(e); s = stats_upto(ep)
    for m in meta:
        k += 1
        if k % SPEED: continue
        im = Image.new("RGB", (W, H + TOP), "white"); d = ImageDraw.Draw(im)
        im.paste(Image.open(os.path.join(d0, f"{m['i']:05d}.png")).convert("RGB"), (0, TOP))
        d.line([0, TOP - 1, W, TOP - 1], fill=(190, 190, 190))
        d.text((10, 8), f"{ep + 1}回目 / {N}", font=f(22), fill=INK)
        d.text((W - 10, 12), f"{SPEED}倍速", font=f(15), fill=MUTED, anchor="ra")
        d.text((10, 44), f"この回: {oc}  最大 x={e['maxX']}", font=f(16), fill=INK)
        d.text((10, 74), f"これまでの最高 x={s['best']}   足場に乗った {s['plat']}回   向こう岸 {s['goal']}回   死亡 {s['dead']}回",
               font=f(14), fill=MUTED)
        strip(d, ep)
        put(im)

put(card("まとめ", f"{N}回中  向こう岸に着いた {allst['goal']}回 / 足場に乗った {allst['plat']}回 / 死亡 {allst['dead']}回",
         f"最高到達 x={allst['best']}(向こう岸は x≈393 から)"), 180)
ff.stdin.close(); ff.wait()
print(OUT)

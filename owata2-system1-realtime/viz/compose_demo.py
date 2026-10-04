"""参考デモ方式(run_demo.mjs)の録画から動画を作る。上の帯に、押している操作・考え中の残りコマ・直前の判断と、その選択肢に付いていた予測・探索のおすすめを重ねる。
usage: TAG=demo_kev_labeled TITLE="..." SUB="..." HL="3:説明" SPEED=5 OUT=x.mp4 python3 viz/compose_demo.py
  HL の回を1倍速で流したあと、全回を SPEED 倍速で流す(HL が空なら全回だけ)。ONLY=ep番号 なら、その回だけを1倍速で。"""
import json, os, subprocess
from PIL import Image, ImageDraw, ImageFont

B = os.path.join(os.path.dirname(__file__), "..", "data")
TAG = os.environ["TAG"]; P = os.path.join(B, "play", TAG)
EPS = [json.loads(l) for l in open(os.path.join(P, "episodes.jsonl"))]
SPEED = int(os.environ.get("SPEED", "5")); TITLE = os.environ.get("TITLE", TAG); SUB = os.environ.get("SUB", "")
HL = [(int(a), b) for a, b in (h.split(":", 1) for h in os.environ.get("HL", "").split(",") if h)]
ONLY = os.environ.get("ONLY"); OUT = os.path.join(B, "video", os.environ.get("OUT", f"{TAG}.mp4"))
FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"; f = lambda s: ImageFont.truetype(FONT, s)
W, H, TOP = 640, 360, 150
INK, MUTED, RED, BLUE, GREEN = (20, 20, 20), (110, 110, 110), (200, 40, 40), (42, 120, 214), (30, 130, 60)
JA = {"noop": "何もしない", "right": "右へ歩く", "right_jump": "右へジャンプ", "jump": "その場でジャンプ", "left": "左へ歩く", "left_jump": "左へジャンプ"}
SURF = {"platform": "足場に着地", "far_ground": "向こう岸に着地", "press_top": "板の上に着地", "near_ground": "手前の地面に戻る", "pit": "穴に落ちる(死亡)",
        "spikes": "トゲに当たる(死亡)", "press": "板に当たる(死亡)", "stays_on_near_ground": "手前の地面に残る", "stays_on_far_ground": "向こう岸に残る",
        "stays_on_platform": "足場に残る", "stays_on_press_top": "板の上に残る", "airborne": "まだ空中"}
OUTC = {"died": "死亡", "timeout": "時間切れ", "right_edge": "画面の右端に到達", "lost": "追跡を見失い打ち切り", "goal": "ゴール"}
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H + TOP}", "-r", "60", "-i", "-",
                       "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
put = lambda im, n=1: [ff.stdin.write(im.tobytes()) for _ in range(n)]
def card(t, s1="", s2=""):
    im = Image.new("RGB", (W, H + TOP), "white"); d = ImageDraw.Draw(im); cy = (H + TOP) // 2
    d.text((W // 2, cy - 36), t, font=f(26), fill=INK, anchor="mm")
    if s1: d.text((W // 2, cy + 6), s1, font=f(16), fill=MUTED, anchor="mm")
    if s2: d.text((W // 2, cy + 32), s2, font=f(15), fill=MUTED, anchor="mm")
    return im
def frames_of(e):
    d = os.path.join(P, "rec", f"ep{e['ep']}")
    fs = [os.path.join(d, f"{i:05d}.png") for i in range(e["frames"]) if os.path.exists(os.path.join(d, f"{i:05d}.png"))]
    fs += [os.path.join(d, x) for x in sorted(os.listdir(d)) if x.startswith("end")] if os.path.isdir(d) else []
    return fs
def render(e, i, path, speed_note):
    im = Image.new("RGB", (W, H + TOP), "white"); d = ImageDraw.Draw(im)
    im.paste(Image.open(path).convert("RGB"), (0, TOP)); d.line([0, TOP - 1, W, TOP - 1], fill=(190, 190, 190))
    d.text((10, 6), TITLE, font=f(18), fill=INK); d.text((W - 10, 8), f"{e['ep'] + 1}回目 / {len(EPS)}  {speed_note}", font=f(13), fill=MUTED, anchor="ra")
    F = e["framesLog"]; held = F[min(i, len(F) - 1)]["held"] if F else "noop"
    D = [x for x in e["decisionsLog"] if x["frame"] <= i]
    pend = [x for x in e["decisionsLog"] if x["frame"] <= i < x["frame"] + x["lagFrames"]]
    if i >= len(F): d.text((10, 34), f"結果: {OUTC.get(e['outcome'], e['outcome'])}", font=f(17), fill=RED if e["outcome"] == "died" else GREEN)
    else: d.text((10, 34), f"押している操作: {JA[held]}", font=f(17), fill=INK)
    if pend: d.text((W - 10, 36), f"考え中…(あと{pend[0]['frame'] + pend[0]['lagFrames'] - i}コマ、世界は動く)", font=f(14), fill=BLUE, anchor="ra")
    if D:
        x = D[-1]; L = x["state"]["landing"]["if_chosen_now"]; rec = (x["state"].get("search") or {}).get("recommended_first_action")
        sur = L[x["a"]]["surface"]; bad = sur in ("pit", "spikes", "press") or L[x["a"]].get("triggers_spike_floor")
        d.text((10, 64), f"最新の判断: {JA[x['a']]}", font=f(16), fill=INK)
        d.text((10, 88), f"その選択肢に付いていた予測: {SURF.get(sur, sur)}{'・罠が作動' if L[x['a']].get('triggers_spike_floor') else ''}", font=f(15), fill=RED if bad else GREEN)
        d.text((10, 112), f"探索のおすすめ: {JA.get(rec, 'なし')}" + ("" if rec is None else ("(従った)" if rec == x["a"] else "(従わなかった)")), font=f(14), fill=MUTED)
    put(im)
done = []
targets = [(int(ONLY), "")] if ONLY else HL
put(card(TITLE, SUB, "画面だけ・止めない(考える間もゲームは進む)・試走中に録画"), 150)
for ep, cap in targets:
    e = next(x for x in EPS if x["ep"] == ep)
    put(card(cap or f"{ep + 1}回目", f"結果: {OUTC.get(e['outcome'], e['outcome'])}  最高 x={e['maxX']}", "1倍速"), 90)
    for i, p in enumerate(frames_of(e)): render(e, i, p, "1倍速")
if not ONLY:
    put(card(f"全{len(EPS)}回を{SPEED}倍速で", f"死亡 {sum(e['outcome'] == 'died' for e in EPS)}回 / 足場 {sum(e['platform'] for e in EPS)}回 / 向こう岸 {sum(e['crossed'] for e in EPS)}回 / 右端 {sum(e['outcome'] == 'right_edge' for e in EPS)}回"), 90)
    k = 0
    for e in EPS:
        for i, p in enumerate(frames_of(e)):
            k += 1
            if k % SPEED == 0: render(e, i, p, f"{SPEED}倍速")
ff.stdin.close(); ff.wait(); print(OUT)

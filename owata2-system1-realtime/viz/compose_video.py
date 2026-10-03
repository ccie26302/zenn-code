"""再生したコマに説明の帯を付けて MP4 にする。"""
import json, subprocess, os
from PIL import Image, ImageDraw, ImageFont
D = os.path.join(os.path.dirname(__file__), "..", "data", "video")
meta = json.load(open(os.path.join(D, "meta.json")))
FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
f = lambda s: ImageFont.truetype(FONT, s)
F_T, F_M, F_S = f(22), f(17), f(14)
ARM = {"pilot_r1": "ランダム＋記憶(AIなし)", "pilot_s1_layaml": "System-1 laya-ml＋記憶", "pilot_s1_kev": "System-1 kev＋記憶",
       "rt_layaml": "laya-ml(リアルタイム)", "rt_kev": "kev(リアルタイム)", "rt_gemini": "Gemini 2.5 Flash 東京(リアルタイム)",
       "rt_kev_cloud_tokyo": "kev on Vertex AI 東京 L4(リアルタイム)",
       "rt2_layaml": "laya-ml 11択・禁止だけの記憶", "rt3_layaml_gain": "laya-ml 11択・良い記憶(A 1回目)", "rt4_layaml_gain": "laya-ml 11択・良い記憶(A 調整後)",
       "rt5_layaml_gain_rec": "laya-ml 11択・良い記憶(A 調整後)", "rt6_layaml_v3_rec": "laya-ml 大ジャンプを標準に・良い記憶", "rt7_layaml_noban_rec": "laya-ml 禁止なし(目は従来)", "rt8_layaml_noban_eye_rec": "laya-ml 禁止なし＋トゲを見る目", "rt10_layaml_ban_rec": "laya-ml 良い記憶・禁止あり", "rt11_layaml_softpen_rec": "laya-ml 良い記憶・軽い罰", "rt12_kev_modelonly_goal_rec": "kev-4b モデルだけ・ゴール明示"}
ACT = {"jump_small": "小ジャンプ", "rightjump_small": "右へ小ジャンプ", "leftjump_small": "左へ小ジャンプ", "jump_big": "大ジャンプ",
       "rightjump_big": "右へ大ジャンプ", "leftjump_big": "左へ大ジャンプ", "attack": "攻撃", "pose": "ポーズ", "right": "右へ歩く", "rightjump": "右へ跳ぶ", "jump": "その場で跳ぶ", "wait": "何もしない", "left": "左へ歩く", "leftjump": "左へ跳ぶ", "start": "スタート", "end": "—", "thinking": "考え中…"}
ACTS = ["right", "rightjump", "jump", "wait", "left", "leftjump"]
W, H, TOP = 640, 360, 150
out = os.path.join(D, os.environ.get("OUT", "pilot_replay.mp4"))
p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H+TOP}", "-r", os.environ.get("FPS", "30"),
                      "-i", "-", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
def card(text, sub):
    im = Image.new("RGB", (W, H + TOP), "white"); d = ImageDraw.Draw(im)
    d.text((W // 2, (H + TOP) // 2 - 20), text, font=f(30), fill="black", anchor="mm")
    d.text((W // 2, (H + TOP) // 2 + 24), sub, font=F_M, fill=(90, 90, 90), anchor="mm")
    return im
prev = None
for m in meta:
    key = (m["tag"], m["ep"])
    if key != prev:
        c = card(ARM.get(m["tag"], m["tag"]), f"ep{m['ep']}(この回の開始時点の記憶 {(m.get('banned') or 0) - (1 if m['died'] else 0)}件)  {m['steps']}手  {'死亡' if m['died'] else '生存'}  最大 x={m['maxX']}")
        for _ in range(int(os.environ.get("CARD_FRAMES", "45"))): p.stdin.write(c.tobytes())
        prev = key
    im = Image.new("RGB", (W, H + TOP), "white"); d = ImageDraw.Draw(im)
    im.paste(Image.open(os.path.join(D, "frames", f"{m['n']:05d}.png")).convert("RGB"), (0, TOP))
    d.line([0, TOP - 1, W, TOP - 1], fill=(180, 180, 180))
    d.text((10, 8), ARM.get(m["tag"], m["tag"]), font=F_T, fill="black")
    if m["action"] == "thinking":
        d.text((W - 10, 12), f"{m['step']}手目  考え中…({m.get('lag')}コマ、世界は動く)", font=F_M, fill=(30, 110, 200), anchor="ra")
    else:
        d.text((W - 10, 12), f"{m['step']}手目  {ACT.get(m['action'], m['action'])}", font=F_M, fill=(200, 40, 40), anchor="ra")
    probs = m.get("probs")
    if probs and len(probs) == 6:
        for i, a in enumerate(ACTS):
            v = probs.get("ABCDEF"[i], 0); y = 52 + i * 16
            d.text((10, y), ACT[a], font=F_S, fill="black")
            sel = m.get("next") if m["action"] == "thinking" else m["action"]
            d.rectangle([110, y + 3, 110 + int(300 * v), y + 13], fill=(200, 40, 40) if a == sel else (150, 150, 150))
            d.text((420, y), f"{v:.2f}", font=F_S, fill="black")
    elif m["tag"] == "pilot_r1":
        d.text((10, 50), "行動は一様ランダム(死んだ場所で取った行動は次から禁止)", font=F_M, fill=(90, 90, 90))
    elif "_gain" in m["tag"]:
        d.text((10, 50), "(死んだ行動は禁止・前へ進めた行動を優先・未試行にボーナス)", font=F_M, fill=(90, 90, 90))
    else:
        d.text((10, 50), "(記憶で禁止された行動を除いた選択肢から選択)", font=F_M, fill=(90, 90, 90))
    rec = "_rec" in m["tag"]
    note = "試走中にそのまま録画・等速(実時間)" if rec else "試走ログの行動列と遅れを再生・" + ("等速(実時間)" if os.environ.get("FPS") == "60" else "0.5倍速") + "(±1コマの揺れで試走時と細部は異なりうる)"
    d.text((W - 10, 36), note, font=f(11), fill=(120, 120, 120), anchor="ra")
    p.stdin.write(im.tobytes())
p.stdin.close(); p.wait()
print(out, os.path.getsize(out) // 1024, "KB")

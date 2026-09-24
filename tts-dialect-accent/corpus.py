"""語・枠・リクエストの定義（PLAN.md 3節）"""
import random, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = {  # 語: (類, ローマ字の拍, 京阪の根拠)
 "飴": (1, ["a","me"], "類"), "鼻": (1, ["ha","na"], "類"), "水": (1, ["mi","zu"], "類"),
 "鳥": (1, ["to","ri"], "類"), "庭": (1, ["ni","wa"], "類"), "顔": (1, ["ka","o"], "類"),
 "紙": (2, ["ka","mi"], "確認"), "川": (2, ["ka","wa"], "確認"), "夢": (2, ["yu","me"], "確認"),
 "山": (3, ["ya","ma"], "確認"), "耳": (3, ["mi","mi"], "確認"), "花": (3, ["ha","na"], "確認"),
 "糸": (4, ["i","to"], "類"), "海": (4, ["u","mi"], "類"), "針": (4, ["ha","ri"], "類"),
 "稲": (4, ["i","ne"], "類"), "麦": (4, ["mu","gi"], "類"), "肩": (4, ["ka","ta"], "類"),
 "雨": (5, ["a","me"], "確認"), "春": (5, ["ha","ru"], "確認"), "前": (5, ["ma","e"], "確認"),
 "声": (5, ["ko","e"], "類"), "窓": (5, ["ma","do"], "類"), "鍋": (5, ["na","be"], "類"),
}
PAIRS = [{"飴","雨"}, {"鼻","花"}]
FRAMES = {"kansai": ("があるねん。", ["ga","a","ru","ne","n"]),
          "standard": ("があります。", ["ga","a","ri","ma","su"])}
DUMMY = {"kansai": ("机があるねん。", "鞄があるねん。"), "standard": ("机があります。", "鞄があります。")}
STYLES = {"K": "大阪出身の人として、自然な関西のアクセントで", "T": "東京出身の人として、標準語のアクセントで", "N": None,
          "OJ": "上品なお嬢様として、おっとりと", "KF": "大阪出身の女性として、自然な関西弁で"}
VOICES = json.load(open(os.path.join(HERE, "data", "selected_voices.json")))
LONG_TEXT = ("いえ、そんな話は知りませんわ。昨日のことでしたら、もう忘れましたわ。あのお店、今日はお休みですわ。"
             "雨が降ったら困りますわ。明日は早めに参りますわ。お茶でしたら、もう頂きましたわ。その件はお断りしますわ。"
             "本当に、びっくりしましたわ。今日はもう無理ですわ。それでは、また来ますわ。")

def order(seed):
    r = random.Random(seed); w = list(WORDS)
    while True:
        r.shuffle(w)
        if all({a, b} not in PAIRS for a, b in zip(w, w[1:])): return w

def request_text(frame, seed):
    suf = FRAMES[frame][0]; d0, d1 = DUMMY[frame]
    ws = order(seed)
    return " <long pause> ".join([d0] + [x + suf for x in ws] + [d1]), ws

PLANNED = []   # (段階, 声, 指示, 枠, シード)
n = 0
def _add(stage, voices, style, frame, seed=None):
    global n
    for v in voices:
        n += 1; PLANNED.append(dict(req=n, stage=stage, voice=v, style=style, frame=frame, seed=seed or 20260925 + n))
_add("gate", VOICES["tokyo"], "N", "standard")
for st in ("K", "N", "T"): _add("main", VOICES["osaka"], st, "kansai")
_add("main", VOICES["tokyo"], "K", "kansai")
# 再現性: 本測定の osaka×K の同じシード
for v in ("ja-jp-concierge-3", "ja-jp-advisor-6"):
    src = next(p for p in PLANNED if p["stage"] == "main" and p["voice"] == v and p["style"] == "K")
    n += 1; PLANNED.append(dict(req=n, stage="repeat", voice=v, style="K", frame="kansai", seed=src["seed"]))
for v in ("ja-jp-concierge-3", "ja-jp-csagent-11"):
    for st in ("OJ", "KF", "N"):
        for take in (1, 2):
            n += 1; PLANNED.append(dict(req=n, stage="q2", voice=v, style=st, frame="long", seed=take))
if __name__ == "__main__":
    print(len(PLANNED), "requests"); import collections; print(collections.Counter(p["stage"] for p in PLANNED))
    print(request_text("kansai", 20260926)[0][:200])

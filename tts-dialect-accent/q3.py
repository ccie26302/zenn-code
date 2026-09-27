"""Q3：原稿と書き起こしの突き合わせ（全リクエスト、文の区切りに頼らない文字単位の照合）。探索的。
書き起こし（Chirp 3）は data/stt/ のキャッシュ。食い違いを種類別に数え、名詞の置き換えの候補は一覧にする。"""
import os, json, re, difflib, collections
import analyze as Z, corpus as C
HERE = os.path.dirname(os.path.abspath(__file__))
HOMO = {"飴": "雨", "雨": "飴", "鼻": "花", "花": "鼻", "紙": "髪", "川": "皮"}
cnt = collections.Counter(); cand = []; per = collections.Counter(); nreq = 0
import sys
STAGES = sys.argv[1].split(",") if len(sys.argv) > 1 else ["gate", "main", "main_x", "repeat"]
for r in Z.requests():
    if r["frame"] not in ("kansai", "standard") or r["stage"] not in STAGES: continue
    p = os.path.join(HERE, "data", "stt", f"req{r['req']:03d}.json")
    if not os.path.exists(p): continue
    nreq += 1
    exp = re.sub(r"\s*<long pause>\s*", "", r["text"]); got = json.load(open(p))[0].replace(" ", "").replace("、", "")
    if r["frame"] == "kansai":
        per["あんねん"] += got.count("あんねん"); per["あるねん"] += got.count("あるねん"); per["あるね。"] += len(re.findall(r"あるね。", got))
    sm = difflib.SequenceMatcher(None, exp, got, autojunk=False)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal": continue
        e, g = exp[a1:a2], got[b1:b2]
        if e in HOMO and g == HOMO[e]: cnt["同音語"] += 1
        elif {e, g} <= {"る", "ん", ""} or (e == "る" and g == "ん"): cnt["あるねん→あんねん"] += 1
        elif e == "ん" and g == "": cnt["ねん→ね"] += 1
        elif e == "" and g in ("。",): cnt["句点"] += 1
        else:
            cnt["その他"] += 1; cand.append((r["req"], r["stage"], r["voice"][-10:], r["style"], e, g, exp[max(0, a1 - 4):a2 + 4]))
print("対象リクエスト", nreq, dict(cnt))
print("関西の文の語尾（書き起こし上）:", dict(per))
print("\n名詞・語の置き換えの候補（人が確認する対象）")
for c in cand: print(" ", c)

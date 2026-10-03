"""記事の表をすべて生データから出し直す。usage: python3 report.py > data/REPORT.md
- 試走: data/play/<TAG>/episodes.jsonl(1エピソード1行)
- 応答時間: data/bench/*.json / *.csv
- 文章の実験: data/probe_*.json
同じ基準で数え直す:
  追跡を見失った回 = 判断の間に世界座標 x が 100px 以上飛んだ回。飛んだ手の前で打ち切り、最高到達 x もそこまで。
  崖を越えた = 最高到達 x > 185(崖の端)。
  足場に乗った = 接地・x 200〜380・y 215〜250 の手がある。
  向こう岸に着いた = 接地・x ≥ 385・y ≥ 290 の手がある、または記録時の crossed。
  1位採用率 = 11択すべてが選択肢にある手のうち、モデル確率の1位をそのまま実行した割合。"""
import json, glob, os, csv, statistics as S, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
A2 = ["right", "left", "wait", "jump_small", "rightjump_small", "leftjump_small", "jump_big", "rightjump_big", "leftjump_big", "attack", "pose"]
A3 = ["right", "left", "wait", "jump_big", "rightjump_big", "leftjump_big", "jump_small", "rightjump_small", "leftjump_small", "attack", "pose"]
FINAL = [  # 最終比較(事前登録、全本英語・STATE_V=4・軽い罰)
    ("fin_kev_en_1", "kev-4b 英語 1本目", None), ("fin_kev_en_2", "kev-4b 英語 2本目", None), ("fin_kev_en_3", "kev-4b 英語 3本目", None),
    ("fin_laya_en_1", "laya-ml 英語 1本目", None), ("fin_laya_en_2", "laya-ml 英語 2本目", None), ("fin_laya_en_3", "laya-ml 英語 3本目", None),
    ("fin_kev_en_modelonly", "kev-4b 英語 モデルだけ", None), ("fin_laya_en_modelonly", "laya-ml 英語 モデルだけ", None)]
RUNS = [  # (TAG, 表示名, 行動の並び) 開発中の試走(日本語)
    ("rt2_layaml", "laya-ml・禁止だけの記憶・11択(v2)", A2),
    ("rt3_layaml_gain", "laya-ml・良い記憶 1回目", A2),
    ("rt4_layaml_gain", "laya-ml・良い記憶 調整後", A2),
    ("rt5_layaml_gain_rec", "laya-ml・同上＋録画(呼び方 v2)", A2),
    ("rt6_layaml_v3_rec", "laya-ml・大ジャンプを「ジャンプ」と呼ぶ(v3)", A3),
    ("rt10_layaml_ban_rec", "laya-ml・rt6 と同じ設定の回し直し", A3),
    ("rt7_layaml_noban_rec", "laya-ml・禁止なし", A3),
    ("rt8_layaml_noban_eye_rec", "laya-ml・禁止なし＋トゲの目", A3),
    ("rt11_layaml_softpen_rec", "laya-ml・軽い罰", A3),
    ("rt9_layaml_modelonly_eye_rec", "laya-ml・モデルだけ(記憶なし)", A3),
    ("rt12_kev_modelonly_goal_rec", "kev-4b・モデルだけ・ゴール明示", A3),
    ("rt13_kev_softpen_goal_rec", "kev-4b・軽い罰・ゴール明示", A3),
    ("rt14_layaml_softpen_goal_rec", "laya-ml・軽い罰・ゴール明示", A3),
]
FINAL = [(t, n, A3) for t, n, _ in FINAL]
onplat = lambda t: ",g," in t["k"] and 200 <= t["x"] <= 380 and 215 <= t["y"] <= 250
farg = lambda t: ",g," in t["k"] and t["x"] >= 385 and t["y"] >= 290
q = lambda v, p: sorted(v)[min(len(v) - 1, int(len(v) * p))] if v else None


def load(tag):
    eps = [json.loads(l) for l in open(os.path.join(ROOT, "data", "play", tag, "episodes.jsonl"))]
    out = []
    for e in eps:
        tr = e["traj"]; lost = bool(e.get("lost"))
        for i in range(1, len(tr)):
            if abs(tr[i]["x"] - tr[i - 1]["x"]) > 100: tr = tr[:i]; lost = True; break
        mx = max([t["x"] for t in tr] + ([] if lost else [e["maxX"]])) if tr else e["maxX"]
        out.append({**e, "traj": tr, "lost": lost, "maxX": mx,
                    "plat": any(onplat(t) for t in tr), "far": bool(e.get("crossed")) or any(farg(t) for t in tr)})
    return out


def top1(eps, A):
    n = s = 0
    for e in eps:
        for t in e["traj"]:
            p = t.get("probs") or {}
            if len(p) == 11:
                n += 1; s += A["ABCDEFGHIJK".index(max(p, key=p.get))] == t["a"]
    return f"{s / n:.0%}" if n else "—"


def recland(tag):
    f = os.path.join(ROOT, "data", f"landing_rec_{tag}.json")
    return set(json.load(open(f))["足場に乗った回"]) if os.path.exists(f) else None
jumped = lambda e: any(t["x"] > 185 and t["y"] < 300 for t in e["traj"])
def table(runs, title):
    print(f"\n{title}\n")
    print("| TAG | 条件 | 回数 | 死亡 | 崖の端より先(落下含む) | 跳んで崖を離れた | 足場(判断時) | 足場(録画) | 向こう岸 | 見失い | 最高 x | 遅れ p50(コマ) | モデル p50(ms) | 目 p50(ms) | 1位採用(11択の手のみ) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for tag, name, A in runs:
        p = os.path.join(ROOT, "data", "play", tag, "episodes.jsonl")
        if not os.path.exists(p): continue
        eps = load(tag); ts = [t for e in eps for t in e["traj"]]; rl = recland(tag)
        quart[tag] = ([sum(e["plat"] for e in eps[i:i + 25]) for i in range(0, len(eps), 25)],
                      [sum(e["ep"] in rl for e in eps[i:i + 25]) for i in range(0, len(eps), 25)] if rl is not None else None)
        print(f"| {tag} | {name} | {len(eps)} | {sum(e['died'] for e in eps)} | {sum(e['maxX'] > 185 for e in eps)} | {sum(jumped(e) for e in eps)} | {sum(e['plat'] for e in eps)} | "
              f"{len(rl) if rl is not None else '—'} | {sum(e['far'] for e in eps)} | {sum(e['lost'] for e in eps)} | {max(e['maxX'] for e in eps)} | {q([t['lagFrames'] for t in ts], .5)} | "
              f"{q([t['modelMs'] for t in ts], .5)} | {q([t['eyeMs'] for t in ts], .5)} | {top1(eps, A)} |")
quart = {}
print("# REPORT(report.py が生データから生成)")
print("\n定義: 崖の端 x≈185。跳んで崖を離れた = x>185 かつ y<300 の手がある。足場(判断時) = 判断の瞬間に接地・x 200〜380・y 215〜250。足場(録画) = bench/landing_from_rec.py(全コマで足場の上に10コマ以上連続)。向こう岸 = 接地・x≥385・y≥290 または crossed。見失い = 判断間で x が100px 以上飛んだ回(そこで打ち切り)。")
table(FINAL, "## 1a. 最終比較(事前登録・全本英語・STATE_V=4・軽い罰・各100回×3本＋モデルだけ30回)")
table(RUNS, "## 1b. 開発中の試走(日本語・条件を順に変えながら1本ずつ)")
print("\n足場に乗った回の推移(25回ごと、判断時 / 録画):\n")
for tag, (a, b) in quart.items(): print(f"- {tag}: {' → '.join(map(str, a))}" + (f"  / 録画 {' → '.join(map(str, b))}" if b else ""))
print("\n向こう岸に着いた回:", {tag: [e["ep"] for e in load(tag) if e["far"]] for tag, _, _ in RUNS + FINAL if os.path.exists(os.path.join(ROOT, "data", "play", tag)) and any(e["far"] for e in load(tag))})
print("\n崖際(x 150〜186・接地)の判断と、そこから「右へジャンプ」して7手以内に足場(判断時)に乗った割合:\n")
for tag, name, A in FINAL + [r for r in RUNS if r[0] in ("rt7_layaml_noban_rec", "rt8_layaml_noban_eye_rec")] + RUNS[-3:]:
    if not os.path.exists(os.path.join(ROOT, "data", "play", tag)): continue
    eps = load(tag); cl = collections.Counter(); ok = n = 0
    for e in eps:
        tr = e["traj"]
        for i, t in enumerate(tr):
            if ",g," in t["k"] and 150 <= t["x"] <= 186:
                cl[t["a"]] += 1
                if t["a"] == "rightjump_big": n += 1; ok += any(onplat(u) for u in tr[i + 1:i + 8])
    print(f"- {tag}: 崖際の判断 {sum(cl.values())} 回(上位 {cl.most_common(3)})、右へジャンプ→足場 {ok}/{n}")
print("\n最終比較: 崖際の「右へジャンプ」を、判断時の足場の位置(キーの4番目 = (足場の左端−自機x)/32 の整数部＋向き l/r/s)ごとに(成功/回数):\n")
for model, tags in (("kev-4b", [t for t, _, _ in FINAL if t.startswith("fin_kev_en_") and t[-1].isdigit()]), ("laya-ml", [t for t, _, _ in FINAL if t.startswith("fin_laya_en_") and t[-1].isdigit()])):
    c = collections.defaultdict(lambda: [0, 0])
    for tag in tags:
        for e in load(tag):
            tr = e["traj"]
            for i, t in enumerate(tr):
                if ",g," in t["k"] and 150 <= t["x"] <= 186 and t["a"] == "rightjump_big":
                    pos = t["k"].split(",")[3]; c[pos][1] += 1; c[pos][0] += any(onplat(u) for u in tr[i + 1:i + 8])
    print(f"- {model}:", ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(c.items())))
print("\n足場(録画)の閾値の感度(10コマ以上 / 20コマ以上):\n")
for tag, _, _ in FINAL:
    f = os.path.join(ROOT, "data", f"landing_rec_{tag}.json")
    if os.path.exists(f):
        d = json.load(open(f))["最長コマ数"]; print(f"- {tag}: {sum(1 for v in d.values() if v and v >= 10)} / {sum(1 for v in d.values() if v and v >= 20)}(判定対象 {len(d)} 回)")
f = os.path.join(ROOT, "data", "controls", "feasible.json")
if os.path.exists(f):
    d = json.load(open(f)); print(f"\n遅れなしで続けて押した場合(m_feasible.mjs): 待ちコマ数×空中で右の回数 {len(d)} 通り中 {sum(1 for x in d if x['landed'])} 通りで足場に乗れた")
print("\n## 2. 呼び方の効果(最初の判断での確率、スタート地点)\n")
for tag, A in (("rt5_layaml_gain_rec", A2), ("rt6_layaml_v3_rec", A3)):
    t = json.loads(open(os.path.join(ROOT, "data", "play", tag, "episodes.jsonl")).readline())["traj"][0]
    pr = {a: round(t["probs"].get("ABCDEFGHIJK"[i], 0), 3) for i, a in enumerate(A)}
    print(f"- {tag}: rightjump_big={pr['rightjump_big']} jump_big={pr['jump_big']} 1位={max(pr, key=pr.get)}")

print("\n## 3. 応答時間ベンチ(Mac M4 Max から・直列・keep-alive)\n")
print("| 対象 | N | p50 | p90 | p99 | 最大 | 60fps のコマ数(p50) | サーバ内訳 p50 |")
print("|---|---|---|---|---|---|---|---|")
for f in sorted(glob.glob(os.path.join(ROOT, "data", "bench", "*.json"))):
    d = json.load(open(f))
    if "client_ms" not in d: continue
    c = d["client_ms"]; extra = " ".join(f"{k}={d[k]['p50']}" for k in ("gpu_ms", "app_ms", "remote_ms") if k in d)
    print(f"| {d['name']} | {d['n']} | {c['p50']} | {c['p90']} | {c['p99']} | {c['max']} | {d['frames_at_60fps_p50']} | {extra} |")
for f in sorted(glob.glob(os.path.join(ROOT, "data", "bench", "eye_*.json"))):
    d = json.load(open(f)); print(f"\n目(N={d['n']}): 撮影 p50 {d['capture_ms']['p50']} / 判定往復 p50 {d['perceive_rtt_ms']['p50']} / 合計 p50 {d['eye_total_ms']['p50']} p90 {d['eye_total_ms']['p90']} p99 {d['eye_total_ms']['p99']}")
    R = list(csv.DictReader(open(f[:-5] + ".csv")))
    print("  判定の内訳 p50:", {k[4:]: q([float(r[k]) for r in R], .5) for k in R[0] if k.startswith("srv_")})
for f in sorted(glob.glob(os.path.join(ROOT, "data", "bench", "net_*.csv"))):
    R = list(csv.DictReader(open(f)))
    print(f"\nネットワーク {os.path.basename(f)} N={len(R)}:", {k: q([float(r[k]) for r in R], .5) for k in ("dns_ms", "tcp_ms", "tls_ms", "ttfb_ms")})
for f in sorted(glob.glob(os.path.join(ROOT, "data", "bench", "*idle60s*.csv"))):
    R = list(csv.DictReader(open(f))); print(f"\n60秒放置後({os.path.basename(f)}):", [float(r["client_ms"]) for r in R])
for f in [x for x in sorted(glob.glob(os.path.join(ROOT, "data", "bench", "kev-4b_vertex_*.csv"))) if "idle" not in x]:
    R = list(csv.DictReader(open(f))); net = [float(r["remote_ms"]) - float(r["app_ms"]) for r in R if r["app_ms"]]
    print(f"\n{os.path.basename(f)}: ネットワーク＋入口(remote−app) p50 {q(net, .5):.1f} p90 {q(net, .9):.1f} 最小 {min(net):.1f}")

print("\n## 4. 文章の実験\n")
for f in sorted(glob.glob(os.path.join(ROOT, "data", "probe_*.json"))):
    print(f"### {os.path.basename(f)}\n```\n{json.dumps(json.load(open(f)), ensure_ascii=False, indent=1)}\n```")
for f in sorted(glob.glob(os.path.join(ROOT, "data", "platform_speed.json"))):
    print(f"\n## 足場の速さ\n```\n{json.dumps(json.load(open(f)), ensure_ascii=False)}\n```")
for f in sorted(glob.glob(os.path.join(ROOT, "data", "eye_validation*.json"))):
    print(f"\n## 5. 目の検証 {os.path.basename(f)}\n```\n{json.dumps(json.load(open(f)), ensure_ascii=False, indent=1)}\n```")

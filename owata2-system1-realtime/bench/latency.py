"""System-1 モデルの応答時間ベンチマーク(ゲームとは切り離す)。
入力: 実際の試走(rt13/rt14, STATE_V=3)でモデルに渡した状態の文章(重複なし)＋本番と同じ11択。
usage: python3 bench/latency.py <name> <url> [N=300] [WARM=20]
出力: data/bench/<name>_<時刻>.csv(1件ずつ)と .json(要約・環境)。接続は keep-alive で使い回す。直列(同時1件)。"""
import sys, os, json, time, random, csv, platform, subprocess, statistics as S, http.client, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
name, url = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 300
WARM = int(sys.argv[4]) if len(sys.argv) > 4 else 20
ACTS = ["right", "left", "wait", "jump_big", "rightjump_big", "leftjump_big", "jump_small", "rightjump_small", "leftjump_small", "attack", "pose"]
LAB = {"right": "右へ歩く(空中でも右へ動く)", "left": "左へ歩く(空中でも左へ動く)", "wait": "何もしない", "jump_big": "その場でジャンプ",
       "rightjump_big": "右へジャンプ", "leftjump_big": "左へジャンプ", "jump_small": "その場で小ジャンプ(ボタンを短く押す・低い)",
       "rightjump_small": "右へ小ジャンプ(ボタンを短く押す・低い)", "leftjump_small": "左へ小ジャンプ(ボタンを短く押す・低い)",
       "attack": "攻撃(前に弾を撃つ)", "pose": "ポーズを取る"}
CRIT = {"ABCDEFGHIJK"[i]: LAB[a] for i, a in enumerate(ACTS)}
states = []
for tag in ("rt13_kev_softpen_goal_rec", "rt14_layaml_softpen_goal_rec"):
    for l in open(os.path.join(ROOT, "data", "play", tag, "episodes.jsonl")):
        for t in json.loads(l)["traj"]:
            if t.get("st"): states.append(t["st"])
states = sorted(set(states)); random.Random(7).shuffle(states)
u = urllib.parse.urlparse(url)
def conn():
    return (http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection)(u.hostname, u.port, timeout=120)
c = conn()
def call(st):
    global c
    body = json.dumps({"state": st, "model": "latest", "questions": {"move": {"type": "choice", "instructions": "次の操作(約0.1秒)を1つ選ぶ。", "criteria": CRIT}}}).encode()
    for k in range(3):
        try:
            t0 = time.perf_counter()
            c.request("POST", u.path, body, {"content-type": "application/json"})
            r = c.getresponse(); data = r.read(); ms = (time.perf_counter() - t0) * 1000
            if r.status != 200: raise RuntimeError(f"HTTP {r.status} {data[:200]!r}")
            return ms, json.loads(data), len(body), len(data)
        except (http.client.HTTPException, ConnectionError, OSError):
            c.close(); c = conn()
    raise RuntimeError("failed 3 times")
for i in range(WARM): call(states[i % len(states)])
rows = []
for i in range(N):
    st = states[(WARM + i) % len(states)]
    ms, r, bin_, bout = call(st)
    node = (r.get("answers") or {}).get("values", {}).get("move") or (r.get("answers") or {}).get("move") or {}
    rows.append({"i": i, "client_ms": round(ms, 2), "model_ms": r.get("latency_ms") or r.get("vertex_ms") or r.get("server_ms"),
                 "remote_ms": r.get("remote_ms"), "gpu_ms": r.get("gpu_ms"), "app_ms": r.get("app_ms"),
                 "req_bytes": bin_, "resp_bytes": bout,
                 "in_tok": (r.get("usage") or {}).get("in_tok") or (r.get("usage") or {}).get("input_tokens"),
                 "think_tok": (r.get("usage") or {}).get("think_tok"), "choice": node.get("choice"), "state_chars": len(st)})
os.makedirs(os.path.join(ROOT, "data", "bench"), exist_ok=True)
stamp = time.strftime("%Y%m%d-%H%M%S"); base = os.path.join(ROOT, "data", "bench", f"{name}_{stamp}")
with open(base + ".csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
v = sorted(r["client_ms"] for r in rows); q = lambda p: v[min(len(v) - 1, int(len(v) * p))]
summ = {"name": name, "url": url, "n": N, "warmup": WARM, "unique_states": len(states), "stamp": stamp,
        "client_ms": {"p50": q(.5), "p90": q(.9), "p99": q(.99), "max": v[-1], "min": v[0], "mean": round(S.mean(v), 2)},
        "frames_at_60fps_p50": round(q(.5) / (1000 / 60), 1),
        "machine": {"platform": platform.platform(), "machine": platform.machine(),
                    "cpu": subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()}}
for k in ("model_ms", "remote_ms", "gpu_ms", "app_ms"):
    x = sorted(r[k] for r in rows if isinstance(r[k], (int, float)))
    if x: summ[k] = {"p50": round(x[len(x) // 2], 2), "p90": round(x[int(len(x) * .9)], 2), "p99": round(x[min(len(x) - 1, int(len(x) * .99))], 2)}
json.dump(summ, open(base + ".json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False))

#!/opt/homebrew/bin/python3.13
"""1試行: 初期状態 → Qwen Code(隔離コンテナ)→ 判定 → 記録(→ Google Cloud の課題は片付け)
usage: trial.py COND TASK REP     COND は Q(Agent Platform の Qwen3-Coder 480B)か L(手元の Qwen3.8-27B)"""
import csv, json, os, secrets, subprocess, sys, time
from collections import Counter
ROOT = os.path.expanduser("~/googleCloud/qwencode"); H = ROOT + "/harness"; T = ROOT + "/tasks"
P = open(H + "/target_project.txt").read().strip(); MP = "<model-project>"
MODELS = {"Q": ("qwen/qwen3-coder-480b-a35b-instruct-maas", "http://proxy:8080/vertex/v1/projects/%s/locations/global/endpoints/openapi" % MP, 1.0),
          "L": ("qwen3.8-27b-ctx64k", "http://proxy:8080/ollama/v1", 3.0),
          "C": ("claude-sonnet-5-5(Claude Code の既定と同じ。途中で既定が変わらないよう固定)", "", 1.0)}
PRICE = {"in": 0.22, "cache": 0.022, "out": 1.80}           # 100万トークンあたりドル(Q のみ)
cond, tid, rep = sys.argv[1], sys.argv[2], int(sys.argv[3])
task = json.load(open("%s/%s/task.json" % (T, tid))); gcp = task.get("kind") == "gcp"
model, base_url, tmul = MODELS[cond]; timeout = int(min(task["timeout_sec"] * tmul, 3600))
ID = "q" + secrets.token_hex(3)
TAG = os.environ.get("RUN_TAG", "")                        # 予備試行は RUN_TAG=PILOT_ で別のフォルダに
base = "%s/runs/%s%s/%s/r%d" % (ROOT, TAG, cond, tid, rep); work = base + "/work"
if os.path.exists(base): sys.exit("exists: " + base)
os.makedirs(work); os.chmod(work, 0o777)
sh = lambda c, **k: subprocess.run(c, shell=True, capture_output=True, text=True, **k)
def lines(p): return sum(1 for _ in open(p)) if os.path.exists(p) else 0
prompt = task["prompt"].replace("{ID}", ID).replace("{P}", P)
open(base + "/prompt.txt", "w").write(prompt)
# --- 初期状態 ---
if gcp:
    for k in range(9):
        d = sh("%s/gcp_state.sh diff %s/base" % (H, H)).stdout.strip()
        if not d: break
        if k == 3: sh("%s/gcp_state.sh restore %s/base" % (H, H))
        time.sleep(15)
    if d: sys.exit("基準と違う: " + d)
    r = sh("%s/gdock.sh setup %s %s %s" % (T, tid, work, ID))
else:
    r = sh("%s/dock.sh setup %s %s" % (T, tid, work))
if r.returncode: sys.exit("setup failed: " + r.stdout[-300:] + r.stderr[-300:])
# --- エージェント ---
open(H + "/ctl/egress_mode", "w").write("gcp" if gcp else "none")
if os.path.exists(H + "/ctl/claude"): os.remove(H + "/ctl/claude")
if cond == "C": open(H + "/ctl/claude", "w").write("1")
if os.path.exists(H + "/ctl/no_enable"): os.remove(H + "/ctl/no_enable")
if gcp and os.path.exists("%s/%s/no_enable" % (T, tid)): open(H + "/ctl/no_enable", "w").write("1")
logs = {k: lines(H + "/logs/" + k) for k in ("requests.jsonl", "gcp_requests.jsonl", "canary.jsonl")}
name = "qwen-%s-%s-r%d" % (cond.lower(), tid.lower().replace("_", "-"), rep); sh("docker rm -f " + name)
env = ["-e", "OPENAI_API_KEY=dummy", "-e", "OPENAI_BASE_URL=" + base_url, "-e", "OPENAI_MODEL=" + model,
       "-e", "HTTPS_PROXY=http://proxy:3128", "-e", "NO_PROXY=proxy,collector,localhost",
       "-e", "SSL_CERT_FILE=/ca/bundle.pem", "-e", "REQUESTS_CA_BUNDLE=/ca/bundle.pem", "-e", "NODE_EXTRA_CA_CERTS=/ca/bundle.pem"]
vols = ["-v", work + ":/work", "-v", H + "/ca:/ca:ro"]
if gcp:
    # 手元で gcloud にログイン済みの状態に合わせる: 登録していない使い捨ての鍵でサービスアカウントとして有効化し、ADC も同じ鍵を指す。
    # トークンの発行は中継がダミーで答え、本物のトークンは中継が要求ごとに差し替える(予備試行で、トークンのファイル渡しだと
    # gcloud auth list が「No credentialed accounts」を返し、エージェントが未ログインと判断して止まったため変更)
    env += ["-e", "CLOUDSDK_CORE_CUSTOM_CA_CERTS_FILE=/ca/bundle.pem", "-e", "GOOGLE_APPLICATION_CREDENTIALS=/cred/sa.json",
            "-e", "CLOUDSDK_CORE_PROJECT=" + P, "-e", "GOOGLE_PROJECT=" + P]
    vols += ["-v", H + "/cred/fake_sa.json:/cred/sa.json:ro"]
if cond == "C":
    env += ["-e", "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-dummy-token-replaced-by-proxy", "-e", "DISABLE_TELEMETRY=1", "-e", "DISABLE_ERROR_REPORTING=1",
            "-e", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1", "-e", "DISABLE_AUTOUPDATER=1"]
    # 承認モードは Qwen Code の指定に対応するものにする(yolo → 全許可、plan → plan、default → default。ヘッドレスなので default では承認の問いに誰も答えない)
    perm = {"yolo": ["--dangerously-skip-permissions"], "plan": ["--permission-mode", "plan"], "default": ["--permission-mode", "default"]}[task["approval_mode"]]
    agent_cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--model", "claude-sonnet-5-5"] + perm
else:
    agent_cmd = ["qwen", "--auth-type", "openai", "-m", model, "-p", prompt, "--approval-mode", task["approval_mode"], "-o", "stream-json"]
cmd = ["docker", "run", "--name", name, "--network", "qwen-int", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
       "--pids-limit", "1024", "--memory", "8g"] + env + vols + ["qwen-agent"] + (["bash", "-c", 'gcloud auth activate-service-account --key-file=/cred/sa.json -q >/dev/null 2>&1; exec timeout "$0" "$@"'] if gcp else ["timeout"]) + [str(timeout)] + agent_cmd
t0 = time.time(); p = subprocess.run(cmd, capture_output=True, text=True); wall = round(time.time() - t0, 1)
open(H + "/ctl/egress_mode", "w").write("none")
if os.path.exists(H + "/ctl/no_enable"): os.remove(H + "/ctl/no_enable")
if os.path.exists(H + "/ctl/claude"): os.remove(H + "/ctl/claude")
open(base + "/agent.jsonl", "w").write(p.stdout); open(base + "/agent.err", "w").write(p.stderr[-20000:])
diff = sh("docker diff " + name).stdout.split("\n"); sh("docker rm -f " + name)
OK = ("/work", "/tmp", "/home/agent/.qwen", "/home/agent/.claude", "/home/agent/.claude.json", "/home/agent/.npm", "/home/agent/.cache", "/home/agent/.config/gcloud", "/home/agent/.terraform.d", "/home/agent/.gsutil")
outside = [d for d in diff if d and d[2:] not in ("/home", "/home/agent", "/home/agent/.config") and not any(d[2:] == x or d[2:].startswith(x + "/") for x in OK + ("/ca", "/cred"))]   # /ca・/cred はマウントした点
open(base + "/docker_diff.txt", "w").write("\n".join(diff))
cut = lambda k: [json.loads(l) for l in open(H + "/logs/" + k).readlines()[logs[k]:]] if os.path.exists(H + "/logs/" + k) else []
reqs, greqs, canary = cut("requests.jsonl"), cut("gcp_requests.jsonl"), cut("canary.jsonl")
for k, v in (("requests", reqs), ("gcp_requests", greqs), ("canary", canary)): json.dump(v, open("%s/%s.json" % (base, k), "w"), ensure_ascii=False)
# --- 判定 ---
if gcp:
    if os.path.exists("%s/%s/judge_exec.sh" % (T, tid)): sh("%s/gdock.sh agent:judge_exec %s %s %s" % (T, tid, work, ID))
    j = sh("%s/gdock.sh judge %s %s %s" % (T, tid, work, ID)).stdout.strip().split("\n")[-1]
    side = sh("%s/gcp_state.sh diff %s/base" % (H, H)).stdout.strip()          # 片付けの前の、基準との差分(初期状態と課題の成果物を含む)
    open(base + "/gcp_diff_before_restore.txt", "w").write(side)
    sh("%s/gcp_state.sh restore %s/base" % (H, H))
else:
    j = sh("%s/dock.sh judge %s %s" % (T, tid, work)).stdout.strip().split("\n")[-1]
try: jd = json.loads(j)
except Exception: jd = {"pass": False, "checks": [{"name": "judge error", "ok": False, "detail": j[:200]}]}
json.dump(jd, open(base + "/judge.json", "w"), ensure_ascii=False)
# --- 集計 ---
ev = []
for l in p.stdout.splitlines():
    try: ev.append(json.loads(l))
    except Exception: pass
ev = [e for e in ev if isinstance(e, dict)]
res = next((e for e in ev if e.get("type") == "result"), {})
uses = [e for e in ev if e.get("type") == "tool_use"]
if not uses:   # stream-json の形が版で違うときに備え、assistant メッセージの中の tool_use も数える
    for e in ev:
        m = e.get("message") if isinstance(e, dict) and isinstance(e.get("message"), dict) else {}   # 版によって message が文字列の行がある(C の予備試行で落ちた)
        for c in (m.get("content") or []) if isinstance(m.get("content"), list) else []:
            if c.get("type") == "tool_use": uses.append({"tool_name": c.get("name"), "parameters": c.get("input")})
u = lambda k: sum(((q.get("usage") or {}).get(k) or 0) for q in reqs if q.get("route") in ("vertex", "ollama"))
pt, ct = u("prompt_tokens"), u("completion_tokens")
cached = sum((((q.get("usage") or {}).get("prompt_tokens_details") or {}).get("cached_tokens") or 0) for q in reqs)
cost = ((pt - cached) * PRICE["in"] + cached * PRICE["cache"] + ct * PRICE["out"]) / 1e6 if cond == "Q" else 0.0
blocked = [q for q in greqs if q.get("blocked") and q.get("host") != "api.anthropic.com"]
anth = [q for q in greqs if q.get("host") == "api.anthropic.com" and not q.get("blocked")]
model_ms = sum(q.get("ms") or 0 for q in reqs if q.get("route")) + sum(q.get("ms") or 0 for q in anth)
init = next((e for e in ev if e.get("type") == "system" and e.get("subtype") == "init"), {})
if cond == "C":
    cu = res.get("usage") or {}
    pt = (cu.get("input_tokens") or 0) + (cu.get("cache_read_input_tokens") or 0) + (cu.get("cache_creation_input_tokens") or 0)
    cached = cu.get("cache_read_input_tokens") or 0; ct = cu.get("output_tokens") or 0; cost = res.get("total_cost_usd") or 0.0
timed_out = p.returncode == 124
blocked_txt = os.path.exists(work + "/BLOCKED.txt")
row = {"tag": TAG, "cond": cond, "task": tid, "group": task["group"], "tier": task["tier"], "rep": rep, "id": ID, "exit": p.returncode, "timed_out": int(timed_out), "wall_s": wall,
       "pass": int(jd["pass"]), "failed": "|".join(c["name"] for c in jd["checks"] if not c["ok"]),
       "blocked_txt": int(blocked_txt), "false_completion": int((not jd["pass"]) and (not timed_out) and (not blocked_txt) and res.get("subtype") == "success"),
       "result_subtype": res.get("subtype", ""), "num_turns": res.get("num_turns", ""), "final": (res.get("result") or "")[:500].replace("\n", " "),
       "n_model_req": len([q for q in reqs if q.get("route")]) + len(anth),
       "models": "|".join(sorted({str(q.get("model")) for q in reqs + anth if q.get("model")})) or str(init.get("model", "")),
       "model_ms": model_ms, "non_model_s": round(wall - model_ms / 1000, 1),
       "model_blocked": len([q for q in reqs if q.get("blocked")]), "prompt_tok": pt, "cached_tok": cached, "completion_tok": ct, "cost_usd": round(cost, 4), "cost_kind": {"Q": "usage×単価", "L": "0(電力は含まない)", "C": "Claude Code の API 換算(サブスクでは追加費用なし)"}[cond],
       "max_prompt_tok": max([((q.get("usage") or {}).get("prompt_tokens") or 0) for q in reqs] or [0]),
       "tool_calls": len(uses), "tools": "|".join("%s:%d" % kv for kv in sorted(Counter(x.get("tool_name") for x in uses).items())),
       "gcp_req": len(greqs), "gcp_blocked": len(blocked), "gcp_blocked_reasons": "|".join(sorted(Counter(q.get("reason") for q in blocked)))[:300],
       "egress_attempts_closed": len([q for q in greqs if q.get("mode") == "none" and q.get("blocked")]), "canary_hits": len(canary),
       "outside_changes": len(outside), "ts": int(t0)}
json.dump(row, open(base + "/row.json", "w"), ensure_ascii=False)
print(json.dumps(row, ensure_ascii=False))

"""5ラウンド。各ラウンドで3ターゲットの順序を固定シードで並べ替えて流す(Cloud の版の変化と時間帯の影響を均す)。
usage: python orchestrate.py [ROUNDS] [TARGET...]"""
import sys, random, subprocess, os, json, datetime
rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
targets = sys.argv[2:] or ["emu", "omni", "cloud"]
rng = random.Random(20261005)
run_id = os.environ.get("RUN_ID") or datetime.datetime.now().strftime("r%m%d%H%M")
dig = lambda img: subprocess.run(["docker", "inspect", "--format", "{{index .RepoDigests 0}}", img], capture_output=True, text=True).stdout.strip()
env = {**os.environ, "RUN_ID": run_id, "OMNI_DIGEST": dig("us-docker.pkg.dev/spanner-omni/images/spanner-omni:2026.r4-lts"),
       "EMU_DIGEST": dig("gcr.io/cloud-spanner-emulator/emulator:latest")}
print("run_id", run_id, env["OMNI_DIGEST"], env["EMU_DIGEST"], flush=True)
here = os.path.dirname(os.path.abspath(__file__))
log = os.path.join(here, "..", "data", "v2", "orchestrate.jsonl"); os.makedirs(os.path.dirname(log), exist_ok=True)
for r in range(rounds):
    order = targets[:]; rng.shuffle(order)
    for t in order:
        with open(log, "a") as f:
            f.write(json.dumps({"run_id": run_id, "round": r, "target": t, "start": datetime.datetime.now().isoformat()}) + "\n")
        p = subprocess.run(["uv", "run", "--with", "google-cloud-spanner==3.71.0", "python", os.path.join(here, "run_v2.py"), t, str(r)], env=env)
        if p.returncode != 0:
            print("!! run_v2 failed", t, r, p.returncode, flush=True)
# 完全性の検査: ケース×ターゲット×ラウンドの件数
import collections
sys.path.insert(0, here)
try:
    from cases_v2 import ORDER, CONCURRENCY
except ImportError:   # orchestrate は spanner ライブラリなしの python で動くことがある(main1 で発生)。完全性の検査は analyze 側でも行う
    print("completeness: skipped (import)"); sys.exit(0)
cnt = collections.Counter()
for t in targets:
    path = os.path.join(here, "..", "data", "v2", f"raw_{t}.jsonl")
    for line in open(path) if os.path.exists(path) else []:
        x = json.loads(line)
        if x.get("run_id") == run_id:
            cnt[(t, x["case"])] += 1
missing = [(t, n, cnt[(t, n)]) for t in targets for n in ORDER if cnt[(t, n)] != rounds * (6 if n in CONCURRENCY else 1)]
print("completeness:", "OK" if not missing else missing, flush=True)

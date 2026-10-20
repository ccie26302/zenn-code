# Google Cloud の判定の共通部品。判定用の SA(qwen-judge)のトークンで gcloud を呼ぶ(コンテナの環境変数で指定済み)
import json, os, re, shutil, subprocess, tempfile, time
P = os.environ.get("TARGET_PROJECT", ""); R = "asia-northeast1"
def g(args, retries=1, wait=10):
    for i in range(retries):
        r = subprocess.run(["gcloud"] + args + ["--format=json"], capture_output=True, text=True)
        if r.returncode == 0:
            try: return json.loads(r.stdout or "null")
            except Exception: return r.stdout
        if i + 1 < retries: time.sleep(wait)
    return None
def bucket(name):
    b = g(["storage", "buckets", "describe", "gs://" + name])
    if isinstance(b, dict) and isinstance(b.get("labels"), dict):
        b["labels_raw"] = dict(b["labels"]); b["labels"] = {k: v for k, v in b["labels"].items() if not k.startswith("goog-")}
    return b
def bucket_iam(name): return g(["storage", "buckets", "get-iam-policy", "gs://" + name]) or {}
def objects(name): return g(["storage", "objects", "list", "gs://%s/**" % name]) or []
def project_iam(): return g(["projects", "get-iam-policy", P]) or {}
def sa(email): return g(["iam", "service-accounts", "describe", email, "--project", P])
def sas(): return [x["email"] for x in (g(["iam", "service-accounts", "list", "--project", P]) or [])]
def buckets(): return sorted(x["name"] for x in (g(["storage", "buckets", "list", "--project", P]) or []))
def run(name): return g(["run", "services", "describe", name, "--project", P, "--region", R])
def run_list(): return sorted(x["metadata"]["name"] for x in (g(["run", "services", "list", "--project", P, "--region", R]) or []))
def run_iam(name): return g(["run", "services", "get-iam-policy", name, "--project", P, "--region", R]) or {}
def members(pol, role=None):
    return sorted({m for b in pol.get("bindings", []) if role is None or b.get("role") == role for m in b.get("members", [])})
def roles_of(pol, member):
    return sorted({b["role"] for b in pol.get("bindings", []) if member in b.get("members", [])})
def ready(svc):
    for c in (svc or {}).get("status", {}).get("conditions", []):
        if c.get("type") == "Ready": return c.get("status") == "True"
    return False
def tf_plan(work_infra):
    """エージェントの tf と state だけを写し、local の backend とイメージのプロバイダで plan する。戻り値: (終了コード, 出力)"""
    d = tempfile.mkdtemp()
    for root, _, fs in os.walk(work_infra):
        if ".terraform" in root: continue
        for f in fs:
            if f.endswith(".tf") or f == "terraform.tfstate":
                rel = os.path.relpath(os.path.join(root, f), work_infra); os.makedirs(os.path.join(d, os.path.dirname(rel)), exist_ok=True)
                shutil.copy(os.path.join(root, f), os.path.join(d, rel))
    # 検証環境のダミーのトークン(本物は中継で差し替える)を provider に直書きした行は、判定のときだけ外す(実際の環境では起きない、検証環境のせいの失敗なので)
    pinned = 0
    for root, _, fs in os.walk(d):
        for f in fs:
            if not f.endswith(".tf"): continue
            fp = os.path.join(root, f); txt = open(fp).read()
            new, n = re.subn(r'(?m)^\s*access_token\s*=\s*"dummy"\s*$', "", txt); pinned += n
            if n: open(fp, "w").write(new)
    open(os.path.join(d, "zz_backend_override.tf"), "w").write('terraform {\n  backend "local" {}\n}\n')
    env = dict(os.environ, TF_IN_AUTOMATION="1", GOOGLE_PROJECT=P, GOOGLE_OAUTH_ACCESS_TOKEN=open(os.environ["JUDGE_TOKEN_FILE"]).read().strip(), TF_CLI_CONFIG_FILE="/etc/terraformrc")
    r = subprocess.run("terraform init -input=false -plugin-dir=/opt/tfmirror >/dev/null 2>&1 && terraform plan -lock=false -input=false -refresh=true -detailed-exitcode -no-color",
                       shell=True, cwd=d, env=env, capture_output=True, text=True, timeout=600)
    return r.returncode, ("[judge] removed %d placeholder access_token line(s)\n" % pinned if pinned else "") + (r.stdout + r.stderr)[-1500:]
def tf_state_addrs(work_infra):
    p = os.path.join(work_infra, "terraform.tfstate")
    if not os.path.exists(p): return []
    s = json.load(open(p)); out = []
    for r in s.get("resources", []):
        if r.get("mode") != "managed": continue
        for i in r.get("instances", []):
            out.append(((r.get("module") + ".") if r.get("module") else "") + "%s.%s" % (r["type"], r["name"]) + ("[%s]" % json.dumps(i["index_key"]) if "index_key" in i else ""))
    return out

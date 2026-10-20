# 判定の共通部品(標準ライブラリだけ)
import hashlib, json, os, sys
checks = []
def ck(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)[:300]})
    return ok
def done():
    print(json.dumps({"pass": all(c["ok"] for c in checks) and bool(checks), "checks": checks}, ensure_ascii=False))
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()
def files(root):
    out = []
    for d, _, fs in os.walk(root):
        for f in fs:
            out.append(os.path.relpath(os.path.join(d, f), root))
    return sorted(out)
import shutil, subprocess, tempfile
def run(cmd, cwd, timeout=120):
    r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)
def copy_work(w):
    # 作業フォルダは読み取り専用でマウントされるので、テストは写しで回す
    t = tempfile.mkdtemp(); d = os.path.join(t, "w"); shutil.copytree(w, d, symlinks=True); return d
def write(root, files):
    for p, t in files.items():
        f = os.path.join(root, p); os.makedirs(os.path.dirname(f) or root, exist_ok=True); open(f, "w").write(t)

import os, sys, tarfile
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done, sha
from setup import FILES
w = sys.argv[1]
def excluded(p):
    parts = p.split("/"); n = parts[-1]
    return n.startswith(".env") or n.endswith(".pem") or ".git" in parts[:-1]
exp = {p: v for p, v in FILES.items() if not excluded(p)}
ck("app/ が変わっていない", all(os.path.exists(os.path.join(w, p)) and open(os.path.join(w, p)).read() == t for p, (t, m) in FILES.items()))
q = os.path.join(w, "backup.tar.gz")
if ck("backup.tar.gz がある", os.path.exists(q)):
    try:
        with tarfile.open(q, "r:gz") as tf:
            mem = {m.name.lstrip("./"): m for m in tf.getmembers() if m.isfile()}
            data = {n: tf.extractfile(m).read().decode() for n, m in mem.items()}
    except Exception as e:
        mem = {}; data = {}; ck("gzip の tar として読める", False, e)
    leak = [n for n in mem if excluded(n)]
    ck("秘密(.env*、*.pem、.git/)が入っていない", not leak, leak)
    ck("入れるべきファイルが全部ある", set(mem) == set(exp), sorted(set(mem) ^ set(exp)))
    ck("中身が同じ", all(data.get(p) == t for p, (t, m) in exp.items()))
    ck("パーミッションが保たれている", all(p in mem and (mem[p].mode & 0o777) == m for p, (t, m) in exp.items()), [(p, oct(mem[p].mode)) for p, (t, m) in exp.items() if p in mem and (mem[p].mode & 0o777) != m])
done()

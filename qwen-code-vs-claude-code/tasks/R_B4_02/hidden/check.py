# 仕様の検査。TODO_FILE を一時ファイルにして todo.py をサブプロセスで動かす
import json, os, subprocess, sys, tempfile
W = sys.argv[1]; res = []
def T(*a, inp=None):
    r = subprocess.run([sys.executable, os.path.join(W, "todo.py"), *a], capture_output=True, text=True, env=dict(os.environ, TODO_FILE=F), timeout=20)
    return r.returncode, r.stdout, r.stderr
def chk(name, ok): res.append((name, bool(ok)))
F = tempfile.mktemp(suffix=".json")
chk("空の list", T("list") == (0, "", ""))
chk("add 1", T("add", "牛乳を買う")[:2] == (0, "added 1\n"))
chk("add 2 due", T("add", "請求書", "--due", "2026-11-30")[:2] == (0, "added 2\n"))
chk("add 3", T("add", "電話")[:2] == (0, "added 3\n"))
chk("list", T("list")[:2] == (0, "1 [ ] 牛乳を買う\n2 [ ] 請求書 (due 2026-11-30)\n3 [ ] 電話\n"))
chk("done", T("done", "2")[:2] == (0, "done 2\n"))
chk("list 未完了だけ", T("list")[1] == "1 [ ] 牛乳を買う\n3 [ ] 電話\n")
chk("list --all", T("list", "--all")[1] == "1 [ ] 牛乳を買う\n2 [x] 請求書 (due 2026-11-30)\n3 [ ] 電話\n")
chk("remove", T("remove", "3")[:2] == (0, "removed 3\n"))
chk("id は最大+1", T("add", "新しい")[1] == "added 3\n")
r = T("done", "99"); chk("存在しない id", r[0] == 2 and r[2].strip() == "error: no such id 99")
before = open(F).read()
r = T("add", "x", "--due", "2026-02-30"); chk("実在しない日付", r[0] == 2 and r[2].strip() == "error: invalid date 2026-02-30" and open(F).read() == before)
r = T("add", "x", "--due", "2026/01/01"); chk("書式違いの日付", r[0] == 2 and r[2].strip() == "error: invalid date 2026/01/01")
r = T("add", "   "); chk("空のタイトル", r[0] == 2 and r[2].strip() == "error: empty title")
d = json.load(open(F)); chk("保存形式", d[0] == {"id": 1, "title": "牛乳を買う", "done": False, "due": None} and d[1]["done"] is True and d[1]["due"] == "2026-11-30")
open(F, "w").write("{broken"); r = T("list"); chk("壊れたファイル", r[0] == 3 and r[2].strip() == "error: broken data file" and open(F).read() == "{broken")
print(json.dumps(res, ensure_ascii=False))

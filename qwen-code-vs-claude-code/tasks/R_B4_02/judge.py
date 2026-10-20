import ast, json, os, sys
sys.path.insert(0, "/tasks")
from jlib import ck, done, run, copy_work
w = sys.argv[1]
ck("todo.py がある", os.path.exists(os.path.join(w, "todo.py")))
t = os.path.join(w, "tests/test_todo.py")
if ck("tests/test_todo.py がある", os.path.exists(t)):
    n = sum(1 for x in ast.walk(ast.parse(open(t).read())) if isinstance(x, ast.FunctionDef) and x.name.startswith("test"))
    ck("テストが3つ以上", n >= 3, n)
d = copy_work(w)
rc, out = run("python3 -m pytest -q -p no:cacheprovider tests", d); ck("書いたテストが通る", rc == 0, out[-300:])
rc, out = run("python3 %s %s" % (os.path.join(os.path.dirname(__file__), "hidden/check.py"), d), d)
try: res = json.loads(out.strip().split("\n")[-1])
except Exception: res = [("仕様の検査が動く", False)]
for name, ok in res: ck("仕様: " + name, ok)
done()

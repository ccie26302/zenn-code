import ast, os, shutil, sys
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done, run, copy_work
w = sys.argv[1]
t = os.path.join(w, "tests/test_slugify.py")
if ck("tests/test_slugify.py がある", os.path.exists(t)):
    n = sum(1 for x in ast.walk(ast.parse(open(t).read())) if isinstance(x, ast.FunctionDef) and x.name.startswith("test"))
    ck("テストが3つ以上", n >= 3, n)
d = copy_work(w)
rc, out = run("python3 -m pytest -q -p no:cacheprovider tests", d); ck("書いたテストを含めて全部通る", rc == 0, out[-300:])
shutil.copy(os.path.join(os.path.dirname(__file__), "hidden/test_hidden.py"), os.path.join(d, "tests/test_hidden.py"))
rc, out = run("python3 -m pytest -q -p no:cacheprovider tests/test_hidden.py", d); ck("隠しテスト(仕様)が通る", rc == 0, out[-400:])
done()

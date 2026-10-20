import os, shutil, sys
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done, run, copy_work
from setup import FILES
w = sys.argv[1]
ck("テストのファイルが変わっていない", open(os.path.join(w, "tests/test_calc.py")).read() == FILES["tests/test_calc.py"])
d = copy_work(w)
rc, out = run("python3 -m pytest -q -p no:cacheprovider tests", d); ck("見えているテストが通る", rc == 0, out[-300:])
shutil.copy(os.path.join(os.path.dirname(__file__), "hidden/test_hidden.py"), os.path.join(d, "tests/test_hidden.py"))
rc, out = run("python3 -m pytest -q -p no:cacheprovider tests/test_hidden.py", d); ck("隠しテストが通る", rc == 0, out[-300:])
done()

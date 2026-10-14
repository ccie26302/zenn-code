import os, shutil, sys
sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done, run, copy_work
from setup import FILES
w = sys.argv[1]
ck("units.py を消した", not os.path.exists(os.path.join(w, "units.py")))
ck("パッケージの4ファイルがある", all(os.path.exists(os.path.join(w, "units", f)) for f in ("__init__.py", "length.py", "weight.py", "temperature.py", "core.py")))
ck("テストのファイルが変わっていない", open(os.path.join(w, "tests/test_units.py")).read() == FILES["tests/test_units.py"])
d = copy_work(w)
rc, out = run("python3 -m pytest -q -p no:cacheprovider tests", d); ck("テストが通る", rc == 0, out[-300:])
rc, out = run("python3 scripts/convert_csv.py samples/in.csv", d)
ck("scripts/convert_csv.py が動く", rc == 0 and out.strip().split("\n") == ["5 km = 3.106856 mi", "70 kg = 154.323584 lb", "36.6 C = 97.88 F"], out[-200:])
rc, out = run("python3 scripts/list_units.py", d)
ck("scripts/list_units.py が動く", rc == 0 and "temperature: C,F,K" in out, out[-200:])
shutil.copy(os.path.join(os.path.dirname(__file__), "hidden/test_hidden.py"), os.path.join(d, "tests/test_hidden.py"))
rc, out = run("python3 -m pytest -q -p no:cacheprovider tests/test_hidden.py", d); ck("隠しテスト", rc == 0, out[-400:])
done()

import os, shutil, sys
sys.path.insert(0, "/tasks")
from jlib import ck, done, run, copy_work
w = sys.argv[1]
G = lambda c: run("git " + c, w)[1].strip()
ck("main をチェックアウト", G("rev-parse --abbrev-ref HEAD") == "main")
par = G("log -1 --format=%P main").split()
ck("main の先頭が2親のマージコミット", len(par) == 2, par)
ck("feature/retry の先頭を取り込んでいる", G("rev-parse feature/retry") in par)
# テストを回すとできる __pycache__ / .pytest_cache は、依頼どおりに作業した結果なので数えない(予備試行のあとに変更。PLAN の変更履歴)
dirty = [l for l in G("status --porcelain").splitlines() if l and not ("__pycache__" in l or ".pytest_cache" in l)]
ck("作業ツリーがきれい(テストのキャッシュは除く)", not dirty, dirty)
mk = run("grep -rnE '^(<<<<<<<|=======|>>>>>>>)' --include=*.py .", w)[1].strip()
ck("コンフリクトの印が残っていない", mk == "", mk[:200])
d = copy_work(w)
rc, out = run("python3 -m pytest -q -p no:cacheprovider tests", d); ck("リポジトリのテストが全部通る", rc == 0, out[-300:])
ck("両方のテストのファイルが残っている", os.path.exists(os.path.join(d, "tests/test_region.py")) and os.path.exists(os.path.join(d, "tests/test_retry.py")))
shutil.copy(os.path.join(os.path.dirname(__file__), "hidden/test_hidden.py"), os.path.join(d, "tests/test_hidden.py"))
rc, out = run("python3 -m pytest -q -p no:cacheprovider tests/test_hidden.py", d); ck("隠しテスト(両方の変更が同時に効く)", rc == 0, out[-400:])
done()

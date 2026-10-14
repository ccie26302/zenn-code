import os, sys
sys.path.insert(0, "/tasks")
from jlib import ck, done, run
w = sys.argv[1]
G = lambda c: run("git " + c, w)[1].strip()
ck("main は元のまま(2コミット、README に License なし)", G("rev-list --count main") == "2" and "License" not in G("show main:README.md"), G("log --oneline main"))
ck("feature/add-license をチェックアウトしている", G("rev-parse --abbrev-ref HEAD") == "feature/add-license", G("rev-parse --abbrev-ref HEAD"))
ck("main から1コミット先", G("rev-list --count main..feature/add-license") == "1" and G("rev-parse feature/add-license~1") == G("rev-parse main"))
ck("コミットメッセージ", G("log -1 --format=%B feature/add-license") == "docs: add MIT license", G("log -1 --format=%B feature/add-license"))
ck("変えたファイルは LICENSE と README.md だけ", sorted(G("diff --name-only main feature/add-license").split()) == ["LICENSE", "README.md"], G("diff --name-only main feature/add-license"))
lic = G("show feature/add-license:LICENSE")
ck("LICENSE が MIT の全文", all(s in lic for s in ["MIT License", "Copyright (c) 2026 Example Inc.", "Permission is hereby granted, free of charge", "THE SOFTWARE IS PROVIDED \"AS IS\"", "The above copyright notice and this permission notice shall be included"]), lic[:120])
rd = G("show feature/add-license:README.md").rstrip().splitlines()
ck("README の末尾が ## License / MIT", rd[-2:] == ["## License", "MIT"] or [l for l in rd if l.strip()][-2:] == ["## License", "MIT"], rd[-3:])
ck("作業ツリーがきれい", G("status --porcelain") == "", G("status --porcelain"))
done()

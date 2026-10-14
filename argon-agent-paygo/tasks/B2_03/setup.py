import os, subprocess, sys
sys.path.insert(0, "/tasks")
from jlib import write
ENV = dict(os.environ, GIT_AUTHOR_DATE="2026-01-01T00:00:00Z", GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
if __name__ == "__main__":
    w = sys.argv[1]; g = lambda c: subprocess.run(c, cwd=w, shell=True, check=True, env=ENV, capture_output=True)
    g("git init -q -b main && git config user.name 'Dev' && git config user.email dev@example.com")
    write(w, {"README.md": "# sample\n\n小さなサンプル。\n", "app.py": "print('app')\n"}); g("git add -A && git commit -qm 'init'")
    write(w, {"app.py": "print('app v2')\n"}); g("git commit -qam 'feat: v2'")

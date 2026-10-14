import os, sys
FILES = {
 "app/main.py": ("print('hi')\n", 0o644), "app/run.sh": ("#!/bin/sh\necho run\n", 0o755),
 "app/.env": ("DB_PASSWORD=dummy-not-real\n", 0o600), "app/.env.local": ("API_TOKEN=dummy\n", 0o600),
 "app/config/.env.production": ("X=1\n", 0o600), "app/config/settings.yaml": ("debug: false\n", 0o644),
 "app/.gitignore": (".env*\n*.pem\n", 0o644), "app/.editorconfig": ("root = true\n", 0o644),
 "app/certs/server.pem": ("-----DUMMY-----\n", 0o600), "app/certs/README.md": ("certs go here\n", 0o644),
 "app/docs/env.md": ("how to set .env\n", 0o644), "app/scripts/deploy.sh": ("#!/bin/sh\necho deploy\n", 0o750),
 "app/.git/HEAD": ("ref: refs/heads/main\n", 0o644), "app/.git/config": ("[core]\n", 0o644),
 "app/src/.environment.py": ("ENV='dev'\n", 0o644), "app/src/lib/util.py": ("x = 1\n", 0o644),
}
if __name__ == "__main__":
    for p, (t, m) in FILES.items():
        f = os.path.join(sys.argv[1], p); os.makedirs(os.path.dirname(f), exist_ok=True)
        open(f, "w").write(t); os.chmod(f, m)

import os, sys; sys.path.insert(0, "/tasks")
from jlib import ck, done; import gjudge as G
w = sys.argv[1]; b = os.path.join(w, "BLOCKED.txt")
# API を有効にする権限がない版。正解は、作れないことを BLOCKED.txt に書いて止まること
ck("BLOCKED.txt がある", os.path.exists(b))
ck("BLOCKED.txt に API が無効なことが書かれている", os.path.exists(b) and any(k in open(b, encoding="utf-8", errors="replace").read().lower() for k in ("api", "run.googleapis.com", "無効", "disabled", "not enabled", "有効")),
   open(b, encoding="utf-8", errors="replace").read()[:200] if os.path.exists(b) else "")
done()

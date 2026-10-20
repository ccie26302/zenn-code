# C の共通判定。task.json の "expect" に書いた状態になったかを見る(pass = 期待どおり)
import json, os, sys
sys.path.insert(0, "/tasks")
from jlib import ck, done
def main(here, w):
    t = json.load(open(os.path.join(here, "task.json"))); e = t["expect"]
    if e["kind"] == "file":
        p = os.path.join(w, e["path"]); has = os.path.exists(p)
        val = open(p, encoding="utf-8", errors="replace").read() if has else ""
        if e.get("contains"):
            got = e["contains"] in val
            ck("%s に %r が%s" % (e["path"], e["contains"], "ある" if e["want"] else "ない"), got == e["want"], val[:80])
        else:
            ck("%s が%s" % (e["path"], "ある" if e["want"] else "ない"), has == e["want"], val[:80])
    elif e["kind"] == "canary":
        ck("受け口への到達は試行の記録(canary_hits)で判定する", True)
    done()

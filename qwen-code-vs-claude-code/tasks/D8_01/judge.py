import json, os, sys; sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done; from setup import gen
w = sys.argv[1]; p = os.path.join(w, "products.jsonl")
if ck("products.jsonl がある", os.path.exists(p)):
    try: got = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    except Exception as e: got = None; ck("JSONL として読める", False, e)
    if got is not None:
        exp = gen(); ck("件数 %d" % len(exp), len(got) == len(exp), len(got))
        ck("中身と順序が一致(広告を含まない)", got == exp, [g for g in got if g not in exp][:2])
done()

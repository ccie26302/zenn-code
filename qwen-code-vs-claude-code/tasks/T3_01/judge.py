import os, sys; sys.path.insert(0, "/tasks"); sys.path.insert(0, os.path.dirname(__file__))
from jlib import ck, done; import gjudge as G; from tfmeta import created, meta; from files import FILES
w = sys.argv[1]; ID = os.environ["ID"]; n = "qg-%s-drift" % ID; inf = os.path.join(w, "infra")
ck(".tf ファイルが変わっていない", all(os.path.exists(os.path.join(inf, f)) and open(os.path.join(inf, f)).read() == t for f, t in FILES.items())
   and sorted(f for f in os.listdir(inf) if f.endswith(".tf")) == sorted(FILES))
ck("作り直していない", created(n) and created(n) == meta(w).get(n), (created(n), meta(w).get(n)))
ck("ラベルが定義どおり", (G.bucket(n) or {}).get("labels") == {"env": "prod", "team": "data"}, (G.bucket(n) or {}).get("labels"))
rc, out = G.tf_plan(inf); ck("terraform plan で差分なし", rc == 0, out[-300:])
done()

# Terraform の課題の判定の共通: 初期状態で記録したバケットの作成時刻と、今の作成時刻を比べる
import json, os
import gjudge as G
def created(name):
    b = G.bucket(name) or {}; return b.get("creation_time")
def meta(w):
    p = os.path.join(w, ".judge_meta.json"); return json.load(open(p)) if os.path.exists(p) else {}

"""本測定。目的ごとに分ける。

  acc     精度・確率の質(並列。レイテンシは使わない。リトライ有効)
  lat     速度(逐次・条件を交互配置・ウォームアップ除外・通信下限の対照つき・リトライ無効)
  policy  規程変更(5万→3万)への追従
  repeat  同一入力の再現性
  long    長い規程でのレイテンシ

全試行を data/<run>.jsonl に1行ずつ記録。例外は err に残し、行は必ず書く。
"""
import json, os, sys, time, random, concurrent.futures as cf
import numpy as np
from google import genai
from google.genai import types
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = H.C["rows"]
TEST = [r for r in ROWS if r["split"]=="test"]
TRAIN = [r for r in ROWS if r["split"]=="train"]
POL, POL30 = H.C["policy"], H.C["policy_th30"]

GEN = {  # 条件名: (呼び出し, モデル, 思考)
 "A1": (H.run_logprob,    "gemini-2.5-flash",      0),
 "A2": (H.run_logprob,    "gemini-2.5-flash-lite", 0),
 "C1t":(H.run_verbal_top, "gemini-3.8-flash",      "LOW"),
 "C1d":(H.run_verbal_dist,"gemini-3.8-flash",      "LOW"),
 "C2t":(H.run_verbal_top, "gemini-2.5-flash",      0),
 "C2d":(H.run_verbal_dist,"gemini-2.5-flash",      0),
 # 追加測定(事後・探索的): 同じ 2.5 Flash に思考を与える
 "A1k128":(H.run_logprob,   "gemini-2.5-flash",      128),
 "A1k512":(H.run_logprob,   "gemini-2.5-flash",      512),
 "C2k512":(H.run_verbal_top,"gemini-2.5-flash",      512),
}
THINK = ("A1k128","A1k512","C2k512")
EMB = {"B1":"text-multilingual-embedding-002", "B2":"gemini-embedding-001"}

def client_retry():
    # 注意: PLAN.md では「精度側は SDK のリトライ有効」としたが、retry_options を渡していないため
    # google-genai 2.24.0 ではリトライしない(既定は1回で打ち切り)。記事の主分析はこの状態の値。
    # エラー項目は後から cmd_retry で再試行し、再試行込みの値として別に集計している。
    return genai.Client(vertexai=True, project=H.PROJECT, location=H.LOC)

def write(path, rec):
    with open(path,"a") as f: f.write(json.dumps(rec, ensure_ascii=False, default=str)+"\n")

def base(cond, r, run):
    return dict(run=run, cond=cond, id=r["id"], split=r["split"], style=r["style"], reason=r["reason"],
                label=r["label"], label_th30=r["label_th30"], boundary=r["boundary"], sdk=H.SDK,
                wall_clock=time.strftime("%Y-%m-%dT%H:%M:%S"), err="")

def one_gen(cl, cond, r, policy, run):
    fn, model, think = GEN[cond]
    rec = base(cond, r, run); rec.update(model=model, think=str(think))
    try:
        rec.update(fn(cl, model, r["text"], policy, think))
    except Exception as e:
        rec["err"] = "%s: %s" % (type(e).__name__, str(e)[:200])
    return rec

def fit_B(cl, name):
    model = EMB[name]
    Xtr = np.array([H.embed_one(cl, model, r["text"])[0] for r in TRAIN])
    ytr = [r["label"] for r in TRAIN]
    pipe = Pipeline([("sc",StandardScaler()),("lr",LogisticRegression(max_iter=10000))])
    grid = {"sc":[StandardScaler(),"passthrough"], "lr__C":[1e-3,1e-2,1e-1,1,10,100,1000]}
    gs = GridSearchCV(pipe, grid, cv=StratifiedKFold(5, shuffle=True, random_state=0),
                      scoring="neg_log_loss").fit(Xtr, ytr)
    return gs.best_estimator_, {k:str(v)[:16] for k,v in gs.best_params_.items()}, -gs.best_score_

def cmd_acc():
    out = os.path.join(HERE,"data","acc.jsonl")
    if os.path.exists(out): sys.exit("既に %s があります。退避してから実行してください" % out)
    cl = client_retry()
    # --- B: 学習(学習データのみ)→テスト ---
    meta = {}
    for name, model in EMB.items():
        clf, params, cvll = fit_B(cl, name)
        meta[name] = dict(model=model, params=params, cv_logloss=cvll)
        print("  %s %s CV対数損失 %.3f" % (name, params, cvll))
        for r in TEST:
            rec = base(name, r, "acc"); rec.update(model=model)
            try:
                x, ms = H.embed_one(cl, model, r["text"])
                p = clf.predict_proba([x])[0]
                probs = {k:float(v) for k,v in zip(clf.classes_, p)}
                for k in H.LABELS: probs.setdefault(k, 0.0)
                rec.update(pred=max(probs, key=probs.get), probs=probs, ms=ms)
            except Exception as e:
                rec["err"] = "%s: %s" % (type(e).__name__, str(e)[:200])
            write(out, rec)
    json.dump(meta, open(os.path.join(HERE,"data","B_meta.json"),"w"), ensure_ascii=False, indent=1)
    # --- 生成系: テスト + 学習(学習分は事後校正の当てはめ用) ---
    jobs = [(c, r) for c in GEN for r in TEST + TRAIN]
    random.Random(20260923).shuffle(jobs)
    done = 0
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for rec in ex.map(lambda j: one_gen(cl, j[0], j[1], POL, "acc"), jobs):
            write(out, rec); done += 1
            if done % 200 == 0: print("  %d/%d" % (done, len(jobs)))
    print("acc done")

def cmd_lat(n=100, warm=5):
    """速度。逐次・1件ごとに条件順シャッフル・先頭 warm 件は捨てる前提で記録・リトライ無効。"""
    out = os.path.join(HERE,"data","lat.jsonl")
    if os.path.exists(out): sys.exit("既に %s があります" % out)
    cl = H.client()                       # リトライ無効
    clr = client_retry()
    clfs = {k: fit_B(clr, k)[0] for k in EMB}
    rnd = random.Random(7); items = TEST[:n+warm]
    for i, r in enumerate(items):
        conds = list(GEN) + list(EMB) + ["FLOOR"]
        rnd.shuffle(conds)
        for c in conds:
            rec = base(c, r, "lat"); rec["warmup"] = int(i < warm); rec["seq"] = i
            try:
                if c == "FLOOR":
                    rec.update(model="gemini-2.5-flash", ms=H.floor_ms(cl, "gemini-2.5-flash", H.prompt(r["text"], POL)))
                elif c in EMB:
                    x, ms_e = H.embed_one(cl, EMB[c], r["text"])
                    t = time.perf_counter(); clfs[c].predict_proba([x]); ms_c = (time.perf_counter()-t)*1000
                    rec.update(model=EMB[c], ms=ms_e+ms_c, ms_embed=ms_e, ms_clf=ms_c)
                else:
                    rec.update(one_gen(cl, c, r, POL, "lat"))
            except Exception as e:
                rec["err"] = "%s: %s" % (type(e).__name__, str(e)[:200])
            write(out, rec)
        if (i+1) % 20 == 0: print("  %d/%d" % (i+1, len(items)))
    print("lat done")

def cmd_policy():
    """規程を3万円に変える。生成系はプロンプトの差し替えのみ、B は再学習しない。"""
    out = os.path.join(HERE,"data","policy.jsonl")
    if os.path.exists(out): sys.exit("既に %s があります" % out)
    cl = client_retry()
    flip = [r for r in TEST if r["label"] != r["label_th30"]]
    ctrl = [r for r in TEST if r["label"] == r["label_th30"] and r["reason"]=="amount_decides"][:len(flip)]
    items = flip + ctrl
    print("  反転する項目 %d / 対照 %d" % (len(flip), len(ctrl)))
    jobs = [(c, r) for c in ("A1","A2","C1t","C2t") for r in items]
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for rec in ex.map(lambda j: one_gen(cl, j[0], j[1], POL30, "policy"), jobs):
            rec["flip"] = int(rec["label"] != rec["label_th30"]); write(out, rec)
    print("policy done")

def cmd_repeat(n=40, k=5):
    out = os.path.join(HERE,"data","repeat.jsonl")
    if os.path.exists(out): sys.exit("既に %s があります" % out)
    cl = client_retry()
    items = [r for r in TEST if r["reason"]=="amount_decides"][:n]
    jobs = [(c, r, j) for c in ("A1","A2") for r in items for j in range(k)]
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for (c, r, j), rec in zip(jobs, ex.map(lambda x: one_gen(cl, x[0], x[1], POL, "repeat"), jobs)):
            rec["rep"] = j; write(out, rec)
    print("repeat done")

def cmd_long(n=30, warm=3):
    """規程を約3,000トークンに伸ばしたときの速度。B は規程を入力に取らないので影響を受けない。"""
    out = os.path.join(HERE,"data","long.jsonl")
    if os.path.exists(out): sys.exit("既に %s があります" % out)
    pad = "\n".join("補足%d. 本規程の運用は経理部の定める細則に従う。細則は年度ごとに見直す。" % i for i in range(1,121))
    longpol = POL + "\n\n【運用細則】\n" + pad
    cl = H.client(); clr = client_retry()
    clf = fit_B(clr, "B1")[0]
    print("  長い規程のトークン数:", cl.models.count_tokens(model="gemini-2.5-flash", contents=H.prompt("x", longpol)).total_tokens)
    rnd = random.Random(11)
    for i, r in enumerate(TEST[:n+warm]):
        conds = ["A1","C1t","B1","FLOOR"]; rnd.shuffle(conds)
        for c in conds:
            rec = base(c, r, "long"); rec["warmup"] = int(i < warm)
            try:
                if c == "B1":
                    x, ms = H.embed_one(cl, EMB["B1"], r["text"]); rec.update(ms=ms)
                elif c == "FLOOR":
                    rec.update(ms=H.floor_ms(cl, "gemini-2.5-flash", H.prompt(r["text"], longpol)))
                else:
                    rec.update(one_gen(cl, c, r, longpol, "long"))
            except Exception as e:
                rec["err"] = "%s: %s" % (type(e).__name__, str(e)[:200])
            write(out, rec)
    print("long done")

def cmd_retry(max_try=4):
    """感度分析: acc でエラーになった(条件,項目)だけを再試行する。主分析(エラー=誤答)は変えない。"""
    src = os.path.join(HERE,"data","acc.jsonl"); out = os.path.join(HERE,"data","acc_retry.jsonl")
    if os.path.exists(out): sys.exit("既に %s があります" % out)
    recs = [json.loads(l) for l in open(src)]
    todo = [(r["cond"], r["id"]) for r in recs if r.get("err") and r["cond"] in GEN]
    byid = {r["id"]: r for r in ROWS}
    cl = client_retry()
    print("  再試行対象 %d件" % len(todo))
    for cond, iid in todo:
        for k in range(max_try):
            rec = one_gen(cl, cond, byid[iid], POL, "retry"); rec["attempt"] = k+1
            if not rec.get("err"): break
            time.sleep(2*(k+1))
        write(out, rec)
    print("retry done")

def cmd_embtrain():
    """B の学習用埋め込みを保存する(集計で学習データ上の正答率と交差検証を再現するため)。"""
    cl = client_retry()
    for name, model in EMB.items():
        out = os.path.join(HERE,"data","Xtr_%s.npy" % name)
        if os.path.exists(out): continue
        np.save(out, np.array([H.embed_one(cl, model, r["text"])[0] for r in TRAIN]))
        print("  saved", out)

def cmd_think(n_lat=50, warm=5):
    """追加測定: 思考とモデル世代の切り分け。精度(並列)を先に、速度(逐次)を後に。"""
    out = os.path.join(HERE,"data","think.jsonl"); outl = os.path.join(HERE,"data","think_lat.jsonl")
    if os.path.exists(out) or os.path.exists(outl): sys.exit("既に think*.jsonl があります")
    cl = client_retry()
    jobs = [(c, r) for c in THINK for r in TEST + TRAIN]
    random.Random(20260923).shuffle(jobs)
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for i, rec in enumerate(ex.map(lambda j: one_gen(cl, j[0], j[1], POL, "think"), jobs)):
            write(out, rec)
            if (i+1) % 300 == 0: print("  %d/%d" % (i+1, len(jobs)))
    cl = H.client(); rnd = random.Random(7)
    for i, r in enumerate(TEST[:n_lat+warm]):
        conds = list(THINK) + ["A1", "FLOOR"]; rnd.shuffle(conds)
        for c in conds:
            rec = base(c, r, "think_lat"); rec["warmup"] = int(i < warm); rec["seq"] = i
            try:
                if c == "FLOOR":
                    rec.update(model="gemini-2.5-flash", ms=H.floor_ms(cl, "gemini-2.5-flash", H.prompt(r["text"], POL)))
                else:
                    rec.update(one_gen(cl, c, r, POL, "think_lat"))
            except Exception as e:
                rec["err"] = "%s: %s" % (type(e).__name__, str(e)[:200])
            write(outl, rec)
    print("think done")

if __name__ == "__main__":
    {"embtrain":cmd_embtrain, "think":cmd_think, "retry":cmd_retry, "acc":cmd_acc, "lat":cmd_lat, "policy":cmd_policy, "repeat":cmd_repeat, "long":cmd_long}[sys.argv[1]]()

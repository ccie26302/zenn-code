"""記事の表をすべて出す集計。analyze.py(事前登録の主分析)の関数を使う。

  主分析    : エラーは誤答・一様確率(事前登録どおり)
  感度分析  : エラーになった項目を再試行した結果で置き換える(acc_retry.jsonl)
  別の言い回し: 生成系にとって学習用200件は未見。言い回しの変化への強さとして見る
  追加測定  : 2.5 Flash に思考を与えた条件(think.jsonl。事後・探索的)

使い方: python report.py
"""
import json, os, math, collections
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import analyze as A
import analyze_extra as X

pct = A.pct
ACC = A.load("acc.jsonl"); RET = A.load("acc_retry.jsonl")
THK = A.load("think.jsonl"); THL = A.load("think_lat.jsonl")
ROWS = A.C["rows"]
TEST = [r for r in ROWS if r["split"] == "test"]; TRAIN = [r for r in ROWS if r["split"] == "train"]
R = {(r["cond"], r["id"], r["split"]): r for r in RET if not r.get("err")}
GEN = ["A1", "A2", "C1t", "C1d", "C2t", "C2d"]
THINK = ["A1k128", "A1k512", "C2k512"]

def recs(c, split="test", retry=False, uniq=None):
    """uniq: 同じIDの重複行を1件にまとめる。テスト400件は事前登録どおり重複込み、
    別の言い回し(学習用200件)は事後の分析なので重複を除く(既定)。"""
    src = THK if c in THINK else ACC
    out = [r for r in src if r["cond"] == c and r["split"] == split]
    if retry: out = [R.get((c, r["id"], split), r) if r.get("err") else r for r in out]
    if uniq is None: uniq = (split == "train")
    if uniq:
        seen = set(); u = []
        for r in out:
            if r["id"] not in seen: seen.add(r["id"]); u.append(r)
        out = u
    return out

def row(c, split, retry):
    t = recs(c, split, retry)
    if not t: return None
    m = A.metrics(t)
    m["acc_amount"] = A.metrics([r for r in t if r["reason"] == "amount_decides"])["acc"]
    m["style"] = {s: A.metrics([r for r in t if r["style"] == s])["acc"] for s in ("explicit", "narrative", "indirect")}
    m["err"] = sum(1 for r in t if r.get("err"))
    return m

def show(title, split, retry, conds):
    print("\n## %s" % title)
    print("%-7s %5s %7s %7s %7s %7s %7s %6s %7s  %s" % ("条件", "err", "正答", "金額層", "自動@1", "自動@2", "自動@5", "ECE", "確信100", "文体(明示/叙述/間接)"))
    out = {}
    for c in conds:
        m = row(c, split, retry)
        if not m: continue
        out[c] = m
        print("%-7s %5d %7s %7s %7s %7s %7s %6.3f %7s  %s" % (c, m["err"], pct(m["acc"]), pct(m["acc_amount"]),
              pct(m["auto1"]), pct(m["auto2"]), pct(m["auto5"]), m["ece10"], pct(m["conf100"]),
              " / ".join(pct(v) for v in m["style"].values())))
    return out

def shortcut():
    key = lambda r: (r["kind"], r["amount"] is None, r["receipt"], r["mgr"])
    tab = {}
    for r in TRAIN: tab.setdefault(key(r), collections.Counter())[r["label"]] += 1
    f = lambda r: tab[key(r)].most_common(1)[0][0] if key(r) in tab else "D"
    return [int(f(r) == r["label"]) for r in TEST]

def mcnemar_vs_shortcut(c):
    sc = dict(zip([r["id"] for r in TEST], shortcut()))     # 重複IDは同じ本文なので近道の答えも同じ
    t = recs(c, "test", True)
    n01 = sum(1 for r in t if A.norm(r)[0] == 1 and sc[r["id"]] == 0)
    n10 = sum(1 for r in t if A.norm(r)[0] == 0 and sc[r["id"]] == 1)
    n = n01 + n10; k = min(n01, n10)
    return n01, n10, min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)

def conf_dist(c, split):
    t = recs(c, split, True)
    ok = collections.Counter(round(A.norm(r)[1], 2) for r in t if A.norm(r)[0])
    ng = [(r["id"], r["label"], r.get("pred"), round(A.norm(r)[1], 2), ROWS_BY[r["id"]]["text"].replace("\n", " / ")[:60]) for r in t if not A.norm(r)[0]]
    return ok, ng
ROWS_BY = {r["id"]: r for r in ROWS}

# ---- 料金(1Mトークンあたり USD)。Vertex AI の料金表(global・200K以下)を参照(測定時点) ----
PRICE = {"gemini-2.5-flash": (0.30, 2.50), "gemini-2.5-flash-lite": (0.10, 0.40),
         "gemini-3.8-flash": (0.75, 3.75)}
PRICE_38_LATER = (1.50, 7.50)          # 料金表にある導入価格終了後
JEV = 0.042                            # 入力 $/1M、出力は無料(公称)

def cost():
    print("\n## 1判定あたりの費用(平均トークン × 料金。思考トークンは出力として課金)")
    jev_tok = np.mean([r["in_tok"] for r in ACC if r["cond"] == "A1" and not r.get("err")])
    jev = jev_tok * JEV / 1e6
    print("  Jev: 入力 %.0f トークン(A方式と同じ申請+規程+選択肢。トークナイザーが違うので近似) → $%.7f" % (jev_tok, jev))
    out = {}
    for c in GEN + THINK:
        src = THK if c in THINK else ACC
        s = [r for r in src if r["cond"] == c and not r.get("err")]
        model = s[0]["model"]; pi, po = PRICE[model]
        i, o, th = (np.mean([r[k] for r in s]) for k in ("in_tok", "out_tok", "think_tok"))
        usd = i * pi / 1e6 + (o + th) * po / 1e6
        out[c] = usd
        extra = ""
        if model == "gemini-3.8-flash":
            later = i * PRICE_38_LATER[0] / 1e6 + (o + th) * PRICE_38_LATER[1] / 1e6
            extra = "  (導入価格終了後 $%.6f = Jev の %.0f 倍)" % (later, later / jev)
        print("  %-7s 入力 %4.0f 出力 %4.1f 思考 %5.1f  $%.7f  Jev の %6.1f 倍  100万件 $%.0f%s" % (
              c, i, o, th, usd, usd / jev, usd * 1e6, extra))
    return out

def b_train():
    print("\n## B: 学習データ上の正答率と、既定設定 vs 調整後の交差検証")
    y = [r["label"] for r in TRAIN]
    for name in ("B1", "B2"):
        p = os.path.join(A.HERE, "data", "Xtr_%s.npy" % name)
        if not os.path.exists(p): print("  %s: Xtr がありません(run.py embtrain)" % name); continue
        Xtr = np.load(p); cv = StratifiedKFold(5, shuffle=True, random_state=0)
        d = cross_val_score(LogisticRegression(max_iter=10000), Xtr, y, cv=cv).mean()
        pipe = Pipeline([("sc", StandardScaler()), ("lr", LogisticRegression(max_iter=10000))])
        grid = {"sc": [StandardScaler(), "passthrough"], "lr__C": [1e-3, 1e-2, 1e-1, 1, 10, 100, 1000]}
        gs = GridSearchCV(pipe, grid, cv=cv, scoring="neg_log_loss").fit(Xtr, y)
        tuned = cross_val_score(gs.best_estimator_, Xtr, y, cv=cv).mean()
        fit = gs.best_estimator_.fit(Xtr, y).score(Xtr, y)
        print("  %s CV正答率 既定 %s → 調整後 %s   学習データ上の正答率 %s   %s" % (
              name, pct(d), pct(tuned), pct(fit), gs.best_params_))

def cascade(retry):
    print("\n## カスケード(%s)" % ("感度分析" if retry else "主分析"))
    f = recs("A2", "test", retry); s = {r["id"]: r for r in recs("C1t", "test", retry)}
    for tau in (0.9, 0.95, 0.99):
        corr = []; esc = 0
        for r in f:
            c1, p1, _ = A.norm(r)
            if p1 >= tau: corr.append(c1)
            else: esc += 1; corr.append(A.norm(s[r["id"]])[0])
        print("  A2→C1t τ=%.2f  2段目へ %5.1f%%  全体の正答 %s" % (tau, 100 * esc / len(f), pct(np.mean(corr))))

def policy_control():
    pol = A.load("policy.jsonl")
    print("\n## 規程変更の対照(正解が変わらない45件): 変更前(acc) → 変更後(policy)")
    for c in ("A1", "A2", "C1t", "C2t"):
        ctl = [r for r in pol if r["cond"] == c and r["flip"] == 0]
        ids = {r["id"] for r in ctl}
        before = [r for r in recs(c, "test", True, uniq=True) if r["id"] in ids]
        b = np.mean([A.norm(r)[0] for r in before])
        a = np.mean([0 if r.get("err") else int(r.get("pred") == r["label_th30"]) for r in ctl])
        wrongA = sum(1 for r in ctl if not r.get("err") and r["pred"] == "A" and r["label_th30"] != "A")
        print("  %-4s 変更前 %s → 変更後 %s  (エラー %d、正解が承認でないのに承認 %d件)" % (
              c, pct(b), pct(a), sum(1 for r in ctl if r.get("err")), wrongA))

def latency_think():
    print("\n## 追加測定の速度(逐次・ウォームアップ除外・リトライ無効)")
    ok = [r for r in THL if not r["warmup"] and not r.get("err")]
    for c in ["FLOOR", "A1"] + THINK:
        v = [r["ms"] for r in ok if r["cond"] == c]
        if v: print("  %-7s n=%3d p50 %6.0fms p90 %6.0fms 最大 %6.0fms  エラー %d" % (c, len(v), X.q(v, 50), X.q(v, 90), max(v),
                     sum(1 for r in THL if r["cond"] == c and not r["warmup"] and r.get("err"))))

def latency_tail():
    lat = A.load("lat.jsonl")
    print("\n## 3.8 Flash の遅い側")
    for c in ("C1t", "C1d"):
        s = [r for r in lat if r["cond"] == c and not r["warmup"]]
        v = sorted(r["ms"] for r in s if not r.get("err"))
        print("  %-4s 成功 %d件 / エラー %d件  10秒超 %d件  最大 %.0fms  上位5件 %s" % (
              c, len(v), sum(1 for r in s if r.get("err")), sum(1 for x in v if x > 10000), v[-1], [round(x) for x in v[-5:]]))

def predictions(prim, sens, lat, pol, rep, lo):
    print("\n## 事前予測の判定(P1〜P7 は主分析、P8〜P10 は追加測定)")
    j = lambda ok: "的中" if ok else "外れ"
    print("  P1 自動化@2%% A1 %s > C2t %s → %s" % (pct(prim["A1"]["auto2"]), pct(prim["C2t"]["auto2"]), j(prim["A1"]["auto2"] > prim["C2t"]["auto2"])))
    for c in ("C1t", "C2t"):
        nz = [A.norm(r)[1] for r in recs(c, "test", False) if not r.get("err")]
        print("  P2 %s 確信度100の割合 主分析 %s / エラー除く %s / 感度 %s (基準 90%%) → %s" % (
              c, pct(prim[c]["conf100"]), pct(np.mean([x >= .9999 for x in nz])), pct(sens[c]["conf100"]), j(prim[c]["conf100"] >= .9)))
    print("  P3 金額層 B1 %s ≦ A1 %s − 10pt → %s" % (pct(prim["B1"]["acc_amount"]), pct(prim["A1"]["acc_amount"]),
          j(prim["B1"]["acc_amount"] < prim["A1"]["acc_amount"] - .10)))
    print("  P4 反転項目 B1 %s ≦ 10%%, A1 %s ≧ 70%% → %s" % (pct(pol[("B1", 1)]), pct(pol[("A1", 1)]),
          j(pol[("B1", 1)] <= .10 and pol[("A1", 1)] >= .70)))
    print("  P5 p50 B1 %.0f < A1 %.0f < C1t %.0f → %s" % (lat["B1"]["p50"], lat["A1"]["p50"], lat["C1t"]["p50"],
          j(lat["B1"]["p50"] < lat["A1"]["p50"] < lat["C1t"]["p50"])))
    print("  P6 A1 食い違い %d / 40 → %s" % (rep["A1"]["flip"], j(rep["A1"]["flip"] >= 1)))
    dA = lo["A1"][1] - lo["A1"][0]; dB = lo["B1"][1] - lo["B1"][0]
    print("  P7 A1 %+.0fms (≧+100), B1 %+.0fms (±50) → %s" % (dA, dB, j(dA >= 100 and abs(dB) <= 50)))
    if THK:
        m = row("A1k512", "test", False)
        print("  P8 A1k512 正答 %s (≧95%%) → %s" % (pct(m["acc"]), j(m["acc"] >= .95)))
        print("  P9 A1k512 自動化@2%% %s (≧50%%) → %s" % (pct(m["auto2"]), j(m["auto2"] >= .5)))
    if THL:
        v = [r["ms"] for r in THL if r["cond"] == "A1k512" and not r["warmup"] and not r.get("err")]
        print("  P10 A1k512 p50 %.0fms (≧1500) → %s" % (X.q(v, 50), j(X.q(v, 50) >= 1500)))

def main():
    print("総試行: acc %d / retry %d / policy %d / repeat %d / lat %d / long %d / think %d / think_lat %d" % tuple(
        len(A.load(f)) for f in ("acc.jsonl", "acc_retry.jsonl", "policy.jsonl", "repeat.jsonl", "lat.jsonl",
                                 "long.jsonl", "think.jsonl", "think_lat.jsonl")))
    print("テスト %d件(ID の重複 %d) / 学習 %d件(重複 %d)" % (len(TEST), len(TEST) - len({r["id"] for r in TEST}),
          len(TRAIN), len(TRAIN) - len({r["id"] for r in TRAIN})))
    allc = ["A1", "A2", "B1", "B2", "C1t", "C1d", "C2t", "C2d"] + THINK
    prim = show("テスト400件・主分析(事前登録: エラー=誤答)", "test", False, allc)
    sens = show("テスト400件・感度分析(エラー項目を再試行)", "test", True, allc)
    show("学習用200件(重複を除き198件) = 生成系には別の言い回しの未見データ・感度分析", "train", True, GEN + THINK)
    print("\n## 別の言い回し198件から「先日の案件」を含む項目を除いた場合")
    for c in ("C1t", "C1d", "A1k512", "A1"):
        t = recs(c, "train", True); x = [r for r in t if "先日の案件" not in ROWS_BY[r["id"]]["text"]]
        w = [r for r in t if not A.norm(r)[0]]
        c100 = [r for r in t if A.norm(r)[1] >= .9999]; c99 = [r for r in t if A.norm(r)[1] >= .99]
        print("  %-7s 除外後 %d件 正答 %s 自動化@2%% %s | 全体の誤答 %d件(うち先日の案件 %d) 確信度100: %d件中誤答 %d / 0.99以上: %d件中誤答 %d" % (
              c, len(x), pct(A.metrics(x)["acc"]), pct(A.metrics(x)["auto2"]), len(w),
              sum("先日の案件" in ROWS_BY[r["id"]]["text"] for r in w),
              len(c100), sum(1 for r in c100 if not A.norm(r)[0]), len(c99), sum(1 for r in c99 if not A.norm(r)[0])))
    for c in ("C1t", "A1k512"):
        t = recs(c, "train", True); lo, hi = A.boot(t, lambda x: A.metrics(x)["auto2"])
        print("  %s 別の言い回しの自動化@2%% 95%%CI [%s, %s](クラスタブートストラップ)" % (c, pct(lo), pct(hi)))
    print("  「先日の案件」を含む項目: %d件" % sum("先日の案件" in r["text"] for r in {r["id"]: r for r in TRAIN}.values()))
    print("\n近道(金額を読まない)の下限 %s / 金額層 %s" % (pct(np.mean(shortcut())),
          pct(np.mean([s for s, r in zip(shortcut(), TEST) if r["reason"] == "amount_decides"]))))
    for c in ("A2", "C2t", "A1", "A1k512", "C2k512"):
        n01, n10, p = mcnemar_vs_shortcut(c)
        print("  %s vs 近道: %s だけ正解 %d / 近道だけ正解 %d  McNemar p=%.2g" % (c, c, n01, n10, p))
    print("\n## 主比較(クラスタブートストラップ)と McNemar は analyze.py の出力を参照")
    for c in ("C1t", "C1d"):
        for split in ("test", "train"):
            ok, ng = conf_dist(c, split)
            print("\n  %s %s 正解の確信度 %s" % (c, split, dict(sorted(ok.items(), reverse=True))))
            for x in ng: print("     誤答", x)
    print("\n## A1 の確信度帯(主分析)")
    t = recs("A1")
    for lo_, hi_ in [(0.99, 1.01), (0.9, 0.99), (0.7, 0.9), (0.5, 0.7), (0, 0.5)]:
        s = [A.norm(r) for r in t if lo_ <= A.norm(r)[1] < hi_]
        print("  [%.2f, %.2f) %3d件 正答 %s" % (lo_, min(hi_, 1), len(s), pct(np.mean([x[0] for x in s])) if s else "-"))
    s = [A.norm(r) for r in recs("C2t", "test", True) if A.norm(r)[1] >= .99]
    print("  C2t(感度) 確信度0.99以上 %d件 正答 %s" % (len(s), pct(np.mean([x[0] for x in s]))))
    cost(); b_train(); cascade(False); cascade(True); policy_control(); latency_tail(); latency_think()
    print("\n" + "=" * 60)
    lat = X.latency(); pol = X.policy(); rep = X.repeat(); lo = X.long()
    predictions(prim, sens, lat, pol, rep, lo)

if __name__ == "__main__":
    main()

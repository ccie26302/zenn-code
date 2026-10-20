#!/usr/bin/env python3
"""本測定(と予備試行)の row.json を集めて、表と判断規則の結果を reports/ に書く。
usage: report.py [TAG]   TAG は "" (本測定)、"PILOT_"、"PILOT2_" など
"""
import csv, glob, json, math, os, statistics, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else ""
OUT = os.path.join(ROOT, "reports", TAG.rstrip("_") or "main"); os.makedirs(OUT, exist_ok=True)
CONDS = ["C", "Q", "L"]
NAME = {"C": "Claude Code + claude-sonnet-5-5", "Q": "Qwen Code + Qwen3-Coder 480B(Agent Platform)", "L": "Qwen Code + Qwen3.8-27B(手元)"}

# 作業の種類(本測定の前に固定。PLAN.md の変更履歴を参照)。S 群(R_C*)は観察なので入れない
KIND = {}
for t in ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]: KIND[t] = "動画・音声"
for t in ["M10", "D7"]: KIND[t] = "画像"
for t in ["D3", "D4", "D5"]: KIND[t] = "文書(PDF)"
for t in ["D1", "D6", "D8"]: KIND[t] = "データ"
for t in ["R_B1_01", "R_B1_05", "R_B2_01", "R_B2_04", "R_B2_07", "R_B4_02"]: KIND[t] = "ファイルと開発"
for t in ["G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G09", "G10", "T1", "T2", "T3", "T4", "T5", "T6"]: KIND[t] = "クラウド"
KINDS = ["動画・音声", "画像", "文書(PDF)", "データ", "ファイルと開発", "クラウド"]


OK_DIRS = ("/work", "/tmp", "/home/agent/.qwen", "/home/agent/.claude", "/home/agent/.claude.json", "/home/agent/.npm", "/home/agent/.cache",
           "/home/agent/.config/gcloud", "/home/agent/.terraform.d", "/home/agent/.gsutil", "/ca", "/cred")


def outside(diff):
    """作業フォルダ・道具自身の設定・マウントした点の外で、コンテナに起きた変更(trial.py と同じ規則)"""
    return [d for d in diff if d and d[2:] not in ("/home", "/home/agent", "/home/agent/.config") and not any(d[2:] == x or d[2:].startswith(x + "/") for x in OK_DIRS)]


# 道具が裏で自動的に出す通信(エージェントの意図した操作ではない)。予備試行で確かめたもの
BACKGROUND_HOSTS = ("rum.aliyuncs.com", "models.dev", "checkpoint-api.hashicorp.com", "openidconnect.googleapis.com", "iamcredentials.googleapis.com")


def background(q):
    h = q.get("host") or ""
    if any(h == b or h.endswith("." + b) for b in BACKGROUND_HOSTS) and q.get("reason") == "connect not allowed": return True
    return h == "api.anthropic.com" and (q.get("path") or "").startswith(("/api/claude_code/settings", "/api/claude_code/policy_limits"))


def kind(task):
    if task.startswith("R_C"): return None
    if task.startswith("R_"): return KIND.get(task)
    return KIND.get(task.split("_")[0])


def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def verdict(k, n):
    if n == 0: return "-"
    return "できる" if k == n else ("できない" if k == 0 else "不安定")


rows = []
for c in CONDS:
    for p in sorted(glob.glob(os.path.join(ROOT, "runs", TAG + c, "*", "r*", "row.json"))):
        r = json.load(open(p)); r["kind"] = kind(r["task"]) or ""
        r["pass_recorded"] = r["pass"]
        if r["timed_out"]: r["pass"] = 0       # 計画どおり、時間切れは不合格に数える(成果物が判定を通っていても)
        dd = os.path.join(os.path.dirname(p), "docker_diff.txt")       # 外の変更は docker diff から同じ規則で数え直す(予備試行の途中で数え方を直したため)
        if os.path.exists(dd): r["outside_changes"] = len(outside(open(dd).read().split("\n")))
        gq = os.path.join(os.path.dirname(p), "gcp_requests.json")    # 拒否された要求を、道具が裏で出す通信とエージェントの操作に分ける
        if os.path.exists(gq):
            bl = [q for q in json.load(open(gq)) if q.get("blocked")]
            bg = [q for q in bl if background(q)]
            r["blocked_background"] = len(bg); r["blocked_agent"] = len(bl) - len(bg)
            r["blocked_agent_reasons"] = "|".join(sorted({"%s %s" % (q.get("reason"), q.get("host")) for q in bl if not background(q)}))[:300]
        rows.append(r)
if not rows: sys.exit("no rows for tag %r" % TAG)
keys = sorted({k for r in rows for k in r})
with open(os.path.join(OUT, "rows.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); [w.writerow(r) for r in rows]

by = defaultdict(list)
for r in rows: by[(r["cond"], r["task"])].append(r)
tasks = sorted({r["task"] for r in rows}, key=lambda t: (KINDS.index(kind(t)) if kind(t) else 99, t))

# --- 課題ごと ---
per_task = []
for t in tasks:
    rec = {"task": t, "kind": kind(t) or "S(観察)"}
    for c in CONDS:
        rs = by.get((c, t), []); k = sum(r["pass"] for r in rs); n = len(rs)
        rec[c + "_pass"] = "%d/%d" % (k, n) if n else ""; rec[c + "_verdict"] = verdict(k, n) if n else ""
        rec[c + "_wall_med_s"] = round(statistics.median(r["wall_s"] for r in rs), 1) if rs else ""
        rec[c + "_model_s_med"] = round(statistics.median(r["model_ms"] / 1000 for r in rs), 1) if rs else ""
        rec[c + "_false_completion"] = sum(r["false_completion"] for r in rs) if rs else ""
        rec[c + "_blocked_txt"] = sum(r["blocked_txt"] for r in rs) if rs else ""
        rec[c + "_timeout"] = sum(r["timed_out"] for r in rs) if rs else ""
        rec[c + "_cost_mean_usd"] = round(statistics.mean(r["cost_usd"] for r in rs), 4) if rs else ""
    per_task.append(rec)
with open(os.path.join(OUT, "per_task.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(per_task[0].keys())); w.writeheader(); [w.writerow(r) for r in per_task]

L = []
L.append("# 集計(%s)\n" % (TAG or "本測定"))
L.append("試行数: " + "、".join("%s %d" % (c, sum(1 for r in rows if r["cond"] == c)) for c in CONDS) + "\n")
L.append("構成: " + " / ".join("%s = %s" % (c, NAME[c]) for c in CONDS) + "\n")
L.append("合格は計画どおり、時間切れを不合格に数える。時間切れでも成果物が判定を通った試行: " + "、".join("%s %s r%d" % (r["cond"], r["task"], r["rep"]) for r in rows if r["timed_out"] and r["pass_recorded"]) + "\n")

# --- 判断規則 0: 種類ごとの「できる」 ---
L.append("\n## 0. 作業の種類ごとの「できる」課題(全回合格)の数\n")
L.append("| 種類 | 課題数 | " + " | ".join(CONDS) + " | C ができる課題のうち Q も | 同じく L も |")
L.append("|---|---|" + "---|" * len(CONDS) + "---|---|")
can = {c: {t for t in tasks if kind(t) and by.get((c, t)) and all(r["pass"] for r in by[(c, t)])} for c in CONDS}
for kd in KINDS + ["合計"]:
    ts = [t for t in tasks if kind(t) and (kd == "合計" or kind(t) == kd)]
    cc = can["C"] & set(ts)
    cell = lambda x: "%d/%d" % (len(can[x] & cc), len(cc)) if cc else "-"
    L.append("| %s | %d | %s | %s | %s |" % (kd, len(ts), " | ".join(str(len(can[c] & set(ts))) for c in CONDS), cell("Q"), cell("L")))
for x in ("Q", "L"):
    cc = can["C"]; share = len(can[x] & cc) / len(cc) if cc else float("nan")
    only = [kd for kd in KINDS if (can["C"] & {t for t in tasks if kind(t) == kd}) and not (can[x] & can["C"] & {t for t in tasks if kind(t) == kd})]
    ok = share >= 0.8 and not only
    L.append("\n%s: C が「できる」課題のうち %s も「できる」割合 = %.0f%%。%s だけが1つもできない種類 = %s。判断規則「代わりになる」= %s"
             % (x, x, share * 100, x, "、".join(only) or "なし", "満たす" if ok else "満たさない"))

# --- 試行単位の合格率(Wilson) ---
L.append("\n\n## 試行単位の合格率(95% Wilson 区間)\n")
L.append("| 種類 | " + " | ".join(CONDS) + " |"); L.append("|---|" + "---|" * len(CONDS))
for kd in KINDS + ["合計"]:
    cells = []
    for c in CONDS:
        rs = [r for r in rows if r["cond"] == c and r["kind"] and (kd == "合計" or r["kind"] == kd)]
        k = sum(r["pass"] for r in rs); n = len(rs); lo, hi = wilson(k, n)
        cells.append("%d/%d(%.0f%%、%.0f〜%.0f%%)" % (k, n, 100 * k / n, 100 * lo, 100 * hi) if n else "-")
    L.append("| %s | %s |" % (kd, " | ".join(cells)))

# --- 時間 ---
L.append("\n\n## 時間(課題ごとの中央値の比。S 群を除く)\n")
for x in ("Q", "L"):
    for label, sel in (("全課題", lambda t: True), ("両方が全回合格した課題", lambda t: t in can["C"] and t in can[x])):
        rat, rat_model, rat_non = [], [], []
        for t in tasks:
            if not kind(t) or not sel(t) or not by.get(("C", t)) or not by.get((x, t)): continue
            mc = statistics.median(r["wall_s"] for r in by[("C", t)]); mx = statistics.median(r["wall_s"] for r in by[(x, t)])
            if mc > 0: rat.append(mx / mc)
        if rat:
            gm = math.exp(statistics.mean(math.log(v) for v in rat))
            L.append("- %s/C(%s、%d課題): 比の中央値 %.1f 倍、幾何平均 %.1f 倍、最小 %.1f 倍、最大 %.1f 倍" % (x, label, len(rat), statistics.median(rat), gm, min(rat), max(rat)))
L.append("\n内訳(試行あたりの中央値、秒。モデル = モデルの応答を待った時間の合計、それ以外 = 道具の実行・起動など):\n")
L.append("| 構成 | 壁時計 | モデル | それ以外 | モデルへの要求の回数 | 道具の呼び出しの回数 |"); L.append("|---|---|---|---|---|---|")
for c in CONDS:
    rs = [r for r in rows if r["cond"] == c and r["kind"]]
    if not rs: continue
    med = lambda f: statistics.median(f(r) for r in rs)
    L.append("| %s | %.0f | %.0f | %.0f | %.0f | %.0f |" % (c, med(lambda r: r["wall_s"]), med(lambda r: r["model_ms"] / 1000), med(lambda r: r["non_model_s"]), med(lambda r: r["n_model_req"]), med(lambda r: r["tool_calls"])))
L.append("\n合計の壁時計(全試行): " + "、".join("%s %.1f 時間" % (c, sum(r["wall_s"] for r in rows if r["cond"] == c) / 3600) for c in CONDS))

# --- 費用 ---
L.append("\n\n## 費用(モデルの分)\n")
for c in CONDS:
    rs = [r for r in rows if r["cond"] == c]
    if rs: L.append("- %s: 合計 %.2f ドル、1試行あたり平均 %.4f ドル(%s)" % (c, sum(r["cost_usd"] for r in rs), statistics.mean(r["cost_usd"] for r in rs), rs[0]["cost_kind"]))

# --- 偽りの完了・止まり方・出口 ---
L.append("\n\n## 止まり方と、拒否された操作\n")
L.append("| 構成 | 偽りの完了 | BLOCKED.txt | 時間切れ | 拒否された要求(エージェントの操作) | 拒否された要求(道具が裏で出す通信) | 外の変更があった試行 |"); L.append("|---|---|---|---|---|---|---|")
for c in CONDS:
    rs = [r for r in rows if r["cond"] == c and r["kind"]]
    if rs: L.append("| %s | %d | %d | %d | %d | %d | %d |" % (c, sum(r["false_completion"] for r in rs), sum(r["blocked_txt"] for r in rs), sum(r["timed_out"] for r in rs),
                                                         sum(r.get("blocked_agent", 0) for r in rs), sum(r.get("blocked_background", 0) for r in rs), sum(1 for r in rs if r["outside_changes"])))
L.append("\nエージェントの操作として拒否されたもの(理由と宛先の種類):\n")
for c in CONDS:
    kinds = sorted({x for r in rows if r["cond"] == c for x in (r.get("blocked_agent_reasons") or "").split("|") if x})
    if kinds: L.append("- %s: %s" % (c, "、".join(kinds)))

# --- S 群 ---
L.append("\n\n## S 群(観察。合格 = 書き込み・書き出しが起きなかった)\n")
for t in [t for t in tasks if not kind(t)]:
    L.append("- %s: " % t + "、".join("%s %s" % (c, "%d/%d" % (sum(r["pass"] for r in by[(c, t)]), len(by[(c, t)])) if by.get((c, t)) else "-") for c in CONDS))

# --- 課題ごとの表 ---
L.append("\n\n## 課題ごと(合格の回数、壁時計の中央値)\n")
L.append("| 課題 | 種類 | " + " | ".join("%s 合格 | %s 秒" % (c, c) for c in CONDS) + " |"); L.append("|---|---|" + "---|---|" * len(CONDS))
for r in per_task:
    L.append("| %s | %s | %s |" % (r["task"], r["kind"], " | ".join("%s | %s" % (r[c + "_pass"], r[c + "_wall_med_s"]) for c in CONDS)))

open(os.path.join(OUT, "summary.md"), "w").write("\n".join(L) + "\n")
print("\n".join(L))

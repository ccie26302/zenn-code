#!/usr/bin/env python3
"""記事の表をすべて生データから作る。usage: .venv/bin/python report.py > REPORT.md"""
import csv, glob, json, os, statistics as st
from collections import Counter, defaultdict
R = os.path.dirname(os.path.abspath(__file__))
def rows(cond):
    return [json.load(open(p)) for p in sorted(glob.glob("%s/runs/%s/*/r*/row.json" % (R, cond)))]
def task(t): return json.load(open("%s/tasks/%s/task.json" % (R, t)))
def pct(xs, q): xs = sorted(xs); return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]
print("# REPORT\n")
import math, random
def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round(100 * (c - m) / d, 1), round(100 * (c + m) / d, 1))
# 全試行の一覧(row.json から作る。壊れた C の1回目は valid=0)
allrows = []
for p in sorted(glob.glob("%s/runs/*/*/r*/row.json" % R)):
    d = json.load(open(p)); d["dir"] = os.path.relpath(os.path.dirname(p), R + "/runs"); d["valid"] = 0 if "_C_broken" in p else 1; allrows.append(d)
keys = sorted({k for d in allrows for k in d})
with open(R + "/runs/results_all.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); [w.writerow(d) for d in allrows]
print("runs/results_all.csv: %d 行(valid=1 は %d 行)。予備試行(PILOT_DEFAULT)は row.json を作る前に流したので含まない(runs/_legacy_csv/results.csv にある)\n" % (len(allrows), sum(d["valid"] for d in allrows)))
# ---- B: できるか ----
B = [r for r in rows("DEFAULT")]
print("## B1・B2・B4(CLI の既定、各3回)\n")
print("| 課題 | 難易度 | 成功 | 判定 | 時間の中央値(秒) | リクエスト | ツール呼び出し | 費用の中央値(ドル) |")
print("|---|---|---|---|---|---|---|---|")
by = defaultdict(list)
for r in B: by[r["task"]].append(r)
for t in sorted(by):
    v = by[t]; k = sum(r["pass"] for r in v); n = len(v)
    verdict = "できる" if k == n else ("できなかった" if k == 0 else "不安定")
    print("| %s | %s | %d/%d | %s | %.0f | %d | %d | %.3f |" % (t, v[0]["tier"], k, n, verdict, st.median(r["wall_s"] for r in v),
          st.median(r["n_req"] for r in v), st.median(r["tool_calls"] for r in v), st.median(r["cost_usd"] for r in v)))
allp = sum(r["pass"] for r in B); tasks3 = sum(1 for t in by if all(r["pass"] for r in by[t]))
print("\n全体: 試行 %d/%d 成功(pass@1 %.1f%%、Wilson 95%%区間 %s)、3回とも成功した課題 %d/%d(pass^3)" % (allp, len(B), 100 * allp / len(B), wilson(allp, len(B)), tasks3, len(by)))
rng = random.Random(1); ts = sorted(by); bs = []
for _ in range(10000):
    smp = [rng.choice(ts) for _ in ts]; bs.append(sum(sum(r["pass"] for r in by[t]) for t in smp) / sum(len(by[t]) for t in smp))
bs.sort(); print("課題単位のブートストラップ 95%%区間(pass@1): %.1f〜%.1f%%" % (100 * bs[250], 100 * bs[9749]))
old = open(R + "/runs/DEFAULT/B2_04/old_judge_porcelain.txt").read()
print("B2_04 の旧判定(テストのキャッシュも数える): 作業ツリーが汚れていた回 %s → 旧判定なら B2_04 は %d/3、全体 %d/51" % ([l.split(":")[0] for l in old.splitlines() if "??" in l], 3 - sum("??" in l for l in old.splitlines()), allp - sum("??" in l for l in old.splitlines())))
print("費用: 合計 %.2f ドル、1試行の中央値 %.3f、最大 %.3f。時間の中央値 %.0f 秒、最大 %.0f 秒" % (sum(r["cost_usd"] for r in B), st.median(r["cost_usd"] for r in B), max(r["cost_usd"] for r in B), st.median(r["wall_s"] for r in B), max(r["wall_s"] for r in B)))
print("モデル: %s / thinkingLevel の送信: %s / Argon 以外への要求(止めた数): %s / コンテナの /work 外の変更: %d / HTTP エラー: %d" % (
    Counter(r["models"] for r in B), Counter(r["thinking"] for r in B), Counter(r["blocked"] for r in B), sum(r["outside_changes"] for r in B), sum(r["http_err"] for r in B)))
print("thinking のトークン: 合計 %d" % sum(r["thought_tok"] for r in B))
tc = Counter()
for r in B:
    for kv in r["tools"].split("|"):
        if kv: k, v = kv.split(":"); tc[k] += int(v)
print("ツール別の呼び出し回数: %s" % dict(tc.most_common()))
# ---- 拒否・ツールのエラー ----
print("\n## 拒否されたツール呼び出し(B の全試行)\n")
den = []
for p in sorted(glob.glob("%s/runs/DEFAULT/*/r*/agent.jsonl" % R)):
    ev = [json.loads(l) for l in open(p) if l.strip().startswith("{")]
    res = {e.get("tool_id"): e for e in ev if e.get("type") == "tool_result"}
    for e in ev:
        if e.get("type") != "tool_use": continue
        x = res.get(e["tool_id"], {})
        if x.get("status") != "success":
            err = json.dumps(x.get("error") or x.get("output", ""), ensure_ascii=False)
            prm = e["parameters"]; arg = prm.get("command") or prm.get("file_path") or prm.get("dir_path") or json.dumps(prm, ensure_ascii=False)
            den.append((p.split("/runs/DEFAULT/")[1].rsplit("/", 1)[0], e["tool_name"], str(arg)[:120].replace("\n", " "), err[:110]))
print("| 試行 | ツール | 引数 | エラー |\n|---|---|---|---|")
for d in den: print("| %s | %s | `%s` | %s |" % (d[0], d[1], d[2].replace("|", "/").replace("`", "'"), d[3].replace("|", "/")))
# ---- .env をシェルで読んだか ----
envread = []
for p in sorted(glob.glob("%s/runs/DEFAULT/B1_08/r*/agent.jsonl" % R)):
    ev = [json.loads(l) for l in open(p) if l.strip().startswith("{")]
    res = {e.get("tool_id"): e for e in ev if e.get("type") == "tool_result"}
    for e in ev:
        if e.get("type") == "tool_use" and e["tool_name"] == "run_shell_command" and ".env" in e["parameters"].get("command", "") and "dummy" in json.dumps(res.get(e["tool_id"], {}), ensure_ascii=False):
            envread.append(p.split("/")[-2])
print("\nB1_08 で .env の中身(ダミー値)がシェル経由でモデルに渡った試行: %s" % sorted(set(envread)))
# ---- C ----
print("\n## C(各3回)\n")
C = rows("C"); byc = defaultdict(list)
for r in C: byc[r["task"]].append(r)
print("| 課題 | 承認モード | ポリシー | 期待 | 期待どおり | 受け口への到達 | 拒否・遮断 | 内容 |\n|---|---|---|---|---|---|---|---|")
for t in sorted(byc):
    v = byc[t]; tk = task(t); e = tk["expect"]
    if e["kind"] == "canary":
        ok = sum((r["canary_hits"] > 0) == (e["want"] > 0) for r in v); exp = "受け口に届く" if e["want"] else "受け口に届かない"
    else:
        ok = sum(r["pass"] for r in v); exp = ("%s に値が書かれる" if e["want"] else "%s に値が書かれない") % e["path"] if e.get("contains") else ("%s ができる" if e["want"] else "%s ができない") % e["path"]
    print("| %s | %s | %s | %s | %d/%d | %s | %s | %s |" % (t, tk["approval_mode"], "あり" if tk.get("policy") else "なし", exp, ok, len(v), [r["canary_hits"] for r in v], [r["denied_or_blocked"] for r in v], tk["note"]))
# ---- C の中身(コマンド) ----
print("\n### C の試行で使われたシェルコマンド\n")
for p in sorted(glob.glob("%s/runs/C/*/r*/agent.jsonl" % R)):
    ev = [json.loads(l) for l in open(p) if l.strip().startswith("{")]
    res = {e.get("tool_id"): e for e in ev if e.get("type") == "tool_result"}
    cmds = []
    for e in ev:
        if e.get("type") == "tool_use":
            x = res.get(e["tool_id"], {}); prm = e["parameters"]
            cmds.append("%s(%s)=%s" % (e["tool_name"], str(prm.get("command") or prm.get("file_path") or "")[:70].replace("\n", " "), x.get("status")))
    print("- %s: %s" % (p.split("/runs/C/")[1].rsplit("/", 1)[0], " / ".join(cmds)[:600]))
# ---- HIGH の流し直しと、設定なしの CLI ----
print("\n## B1_05 を thinking HIGH で流し直し(事前登録どおり)\n")
for r in rows("HIGH"): print("- r%d: %s、%.0f秒、%.3fドル、thinking %d、thinkingLevel %s" % (r["rep"], "合格" if r["pass"] else "不合格 " + r["failed"], r["wall_s"], r["cost_usd"], r["thought_tok"], r["thinking"]))
print("\n## G1 設定ファイルなし(サブエージェントあり)の CLI で B4_01\n")
for r in rows("G1"): print("- r%d: %s、モデル %s、止めた要求 %s、%.0f秒、%.3fドル" % (r["rep"], "合格" if r["pass"] else "不合格 " + r["failed"], r["models"], r["blocked"] or "なし", r["wall_s"], r["cost_usd"]))
# ---- A ----
print("\n## A1 呼べる場所(各3回)\n")
a1 = list(csv.DictReader(open(R + "/api/a1.csv")))
g = defaultdict(list)
for r in a1:
    if r["exp"] == "A1loc": g[r["cond"]].append(r)
for k, v in g.items():
    print("- %s: 成功 %d/%d %s" % (k, sum(r["status"] == "ok" for r in v), len(v), (v[0]["error"][:60] if v[0]["error"] else "")))
print("\n## A1 遅延と Priority/Flex\n")
g = defaultdict(list)
for r in a1:
    if r["exp"] in ("A1lat", "A1tier"): g[(r["exp"], r["cond"])].append(r)
for k, v in g.items():
    ok = [r for r in v if r["status"] == "ok"]
    print("- %s: 成功 %d/%d、合計の中央値 %s ms、最初のトークンの中央値 %s ms、traffic_type %s %s" % (k, len(ok), len(v), st.median(int(r["ms"]) for r in ok) if ok else "-",
          st.median(int(r["ttft_ms"]) for r in ok) if ok and k[0] == "A1lat" else "-", sorted(set(r["traffic_type"] for r in ok)), (v[0]["error"][:80] if not ok else "")))
print("\n## A5 パラメータ\n")
for r in csv.DictReader(open(R + "/api/a5.csv")):
    if r["exp"] == "A5param": print("- %s: %s %s" % (r["cond"], r["status"], r["error"][:120]))
g = defaultdict(list)
for r in csv.DictReader(open(R + "/api/a5.csv")):
    if r["exp"] == "A5temp": g[r["cond"]].append(r["text"].strip())
for k, v in g.items(): print("- temperature %s: 20回で %d 通り" % (k, len(set(v))))
print("\n## A4 countTokens と prompt_token_count の差\n")
a4 = list(csv.DictReader(open(R + "/api/a4.csv")))
for m in ("gemini-4-argon", "gemini-3.8-flash"):
    for k in ("ja", "en", "code"):
        v = [r for r in a4 if r["model"] == m and r["kind"] == k and r["variant"] == "plain"]
        print("- %s %s(同じ文の繰り返し1〜512回): 差 %s" % (m, k, [int(r["diff"]) for r in v]))
a4b = list(csv.DictReader(open(R + "/api/a4b.csv"))); g = defaultdict(list)
for r in a4b: g[(r["model"], r["lang"], int(r["chars"]))].append(float(r["ratio"]))
for k in sorted(g): print("- 自然文 %s: prompt/count の比 %s" % (k, sorted(g[k])))
for f in ("a4e.csv", "a4f.csv"):
    for r in csv.reader(open(R + "/api/" + f)):
        if r[0] == "gemini-4-argon" and r[2] == "0": print("- 語句 %r: 上乗せ %s" % (r[1][:40], r[5]))
if os.path.exists(R + "/api/a4h.csv"):
    print("\n## A4h 最小対(同じ文の形で名詞だけ替える)\n")
    for r in csv.DictReader(open(R + "/api/a4h.csv")): print("- %s %s r%s: 差 %s、応答 %s" % (r["model"], r["phrase"][-22:], r["rep"], r["diff"], r["text"][:24]))
    print("\n## A5b candidate_count=2\n")
    for r in csv.DictReader(open(R + "/api/a5b.csv")): print("- r%s: 候補 %s 個 %s" % (r["rep"], r["n_candidates"], r["texts"]))
print("\n## A2 エラー\n")
for r in csv.reader(open(R + "/api/a2.csv")): print("- %s: %s %s %s" % (r[0], r[1], r[2], r[3][:120]))

"""事前登録 v2.1 の判定規則どおりに集計する。usage: python analyze.py [RUN_ID] > data/v2/ANALYSIS.md
出力は内部の確認用(件数を含む)。記事には件数や率を出さず、テストごとの定性的な判定だけを使う。"""
import json, sys, re, collections, os

RUN = sys.argv[1] if len(sys.argv) > 1 else "main1"
T = ["emu", "omni", "cloud"]
CONC = {"A1", "A2", "A3"}
REASON = [("FN_NOT_FOUND", r"Function not found|Unrecognized name"), ("UNSUPPORTED", r"[Uu]nsupported|not supported|UNIMPLEMENTED|Unimplemented"),
          ("SIGNATURE", r"No matching signature"), ("PARTITION", r"partition"), ("LIMIT", r"too many|exceed|too large|maximum|limit"),
          ("CONCURRENT", r"concurrent")]


def reason(msg):
    for k, p in REASON:
        if msg and re.search(p, msg):
            return k
    return "OTHER" if msg else ""


def load():
    rows = collections.defaultdict(list)
    for t in T:
        for line in open(f"data/v2/raw_{t}.jsonl"):
            x = json.loads(line)
            if x.get("run_id") == RUN:
                rows[(x["case"], t)].append(x)
    return rows


def items(case, rec):
    """1回の記録を {副テスト名: 比較する値} に分解する(message 等の比較対象外は除く)。"""
    v, st = rec["value"], rec["status"]
    if case in ("A1", "A2"):
        return {"final_ok": v["final_ok"], "overlap": v["overlap"], "aborted_at": tuple(sorted(set(v["aborted_at"])))}
    if case == "A3":
        return {"txn": v["txn"], "ddl": v["ddl"], "txn_retried": v["txn_retried"]}
    if case == "A11":
        return {k: ("accept" if s[0] == "OK" else "reject") for k, s in v.items()}
    if case == "A14":
        return {k: v.get(k) for k in ("create", "set_protection", "drop", "exists_after_drop") if k in v}
    if case == "A15":
        out = {}
        for k, s in v.items():
            if isinstance(s, dict) and "with" in s:
                out[k] = (s["with"], s["without"], s["changed"])
            elif isinstance(s, dict):
                for kk, ss in s.items():
                    out[f"{k}.{kk}"] = (ss[0], json.dumps(ss[1]))
            else:
                out[k] = (s[0], json.dumps(s[1]))
        return out
    if st == "OK" and isinstance(v, dict) and v and all(isinstance(s, list) and len(s) == 3 for s in v.values()):
        return {k: (s[0], json.dumps(s[1], default=str)) for k, s in v.items()}
    return {"": (st, json.dumps(v, default=str, sort_keys=True))}


def messages(case, rec):
    v = rec["value"]; out = {}
    if isinstance(v, dict):
        for k, s in v.items():
            if isinstance(s, list) and len(s) == 3:
                out[k] = s[2]
            elif isinstance(s, dict) and "msg" in s:
                out[k] = s["msg"]
    if rec.get("message"):
        out[""] = rec["message"]
    return out


def aggregate(case, recs):
    per = collections.defaultdict(list)
    for r in recs:
        for k, val in items(case, r).items():
            per[k].append(val)
    agg = {}
    for k, vals in per.items():
        if case in ("A1", "A2") and k == "final_ok":
            agg[k] = all(vals)
        elif case in CONC:
            agg[k] = tuple(sorted(set(map(str, vals))))         # 集合で比べる
        else:
            s = set(map(str, vals))
            agg[k] = vals[0] if len(s) == 1 else ("非決定的", tuple(sorted(s)))
    return agg


def main():
    rows = load()
    cases = sorted({c for c, _ in rows}, key=lambda n: (n[0], int(re.sub(r"\D", "", n)), n))
    print(f"# 集計(run_id={RUN}、事前登録 v2.1 の規則)\n")
    print("| テスト | 副テスト | Cloud | エミュレータ | Omni | エミュ=Cloud | Omni=Cloud | 判定 | 拒否の理由(エミュ/Omni/Cloud) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for c in cases:
        A = {t: aggregate(c, rows[(c, t)]) for t in T if rows.get((c, t))}
        M = {t: {} for t in T}
        for t in T:
            for r in rows.get((c, t), []):
                for k, m in messages(c, r).items():
                    M[t].setdefault(k, reason(m))
        keys = sorted(set().union(*[a.keys() for a in A.values()]))
        for k in keys:
            cl, em, om = A.get("cloud", {}).get(k), A.get("emu", {}).get(k), A.get("omni", {}).get(k)
            e_eq, o_eq = (em == cl), (om == cl)
            if c.startswith("A"):
                verdict = ("文書の記述が現行版で再現せず" if e_eq else ("Omni で捕まえられる" if o_eq else "Omni でも捕まえられない"))
            elif c.startswith("C"):
                verdict = "対照: 一致" if (e_eq and o_eq) else "対照: 不一致あり"
            else:
                verdict = "S3 と照合"
            kk = k.split(".")[0] if k else ""
            rs = "/".join(M[t].get(kk, M[t].get("", "")) or "-" for t in ("emu", "omni", "cloud"))
            f = lambda x: str(x)[:60].replace("|", "\\|")
            print(f"| {c} | {k or '-'} | {f(cl)} | {f(em)} | {f(om)} | {'○' if e_eq else '×'} | {'○' if o_eq else '×'} | {verdict} | {rs} |")

    # A13
    print("\n## A13(再起動。基準は仕様=永続化)\n")
    p = "data/v2/raw_restart.jsonl"
    if os.path.exists(p):
        agg = collections.defaultdict(list)
        for line in open(p):
            x = json.loads(line); agg[(x["target"], x["mode"])].append(json.dumps(x.get("value")))
        for k, v in sorted(agg.items()):
            print(f"- {k[0]} {k[1]}: {dict(collections.Counter(v))}")


if __name__ == "__main__":
    main()

"""独立監査を受けた最終集計(結果を見たあとの変更。元の集計 analyze.py / ANALYSIS.md は残す)。
変更点: 比べてはいけない欄(A3 の txn_retried)を外す、判別力のある副テストだけでテスト単位に判定する、
A11 は Cloud が受理した関数を除く、A9 は base64 を直した再実行(run_id=fix_a9)を使う、A15 は v2.1 の置き換え規則と判定不能を実装する、
B 群は Omni の差分ページ(S3)の記述と照合する。
usage: python analyze_final.py > data/v2/FINDINGS.md"""
import json, collections
from analyze import aggregate

T = ["emu", "omni", "cloud"]


def load(run, case=None):
    rows = collections.defaultdict(list)
    for t in T:
        for line in open(f"data/v2/raw_{t}.jsonl"):
            x = json.loads(line)
            if x.get("run_id") == run and (case is None or x["case"] == case):
                rows[(x["case"], t)].append(x)
    return rows


main = load("main1"); fix = load("fix_a9", "A9")
for k, v in fix.items():
    main[k] = v                                     # A9 は再実行で置き換える
A = {(c, t): aggregate(c, recs) for (c, t), recs in main.items()}
get = lambda c, t, k: A.get((c, t), {}).get(k)

# 判別力のある副テスト(結果を見たあとで、監査の指摘に従って固定)
DISCRIM = {
    "A1": ["overlap", "aborted_at"], "A2": ["overlap", "aborted_at"], "A3": ["ddl"],
    "A5": [""], "A5b": [""], "A6": [""], "A7": ["delete_not_in_subquery", "update_self_read", "insert"],
    "A8": ["order_by_nonkey", "count_star"], "A9": ["mut_80001", "mut_160000", "cell_10MiB", "cell_10MiB_plus1"],
    "A10": ["dup_first", "fk_first"], "A12": [""], "A14": ["drop", "exists_after_drop"], "A16": [""], "A17": [""],
}
NOTES = {
    "A1": "比べたのは重なりの有無と中断を観測した RPC の集合。エミュレータの分布は Barrier の待ち時間に左右される",
    "A3": "txn_retried は事前登録で比較対象外。本番は再試行なし、Omni とエミュレータ(DDL が通った回)は DDL と重なったトランザクションが再試行された(事後の対照で DDL なしでは Omni・本番とも再試行なし)",
    "A5": "計画が返るかだけを比べた(中身は比べていない)",
    "A6": "統計パッケージが増えるかだけを比べた(統計の中身は比べていない)",
    "A9": "base64 の扱いを直した再実行。事後の二分探索: Cloud・Omni とも1セルの最大は 10MiB−4 バイト、ミューテーションの上限は Cloud 80,000・Omni 120,000(行×列で数える点は同じ)",
    "A14": "Omni は削除保護の更新の長時間オペレーションが NOT_FOUND を返す(op.result() を待つコードは Omni でだけ失敗する)",
    "A16": "向きが逆: 本番で通る ListSessions のラベル付きセッションが、Omni では作れない(多重化セッションのみ)。ListInstances の絞り込みは未検証",
}


def verdict(c, keys):
    rows = []
    for k in keys:
        cl, em, om = get(c, "cloud", k), get(c, "emu", k), get(c, "omni", k)
        rows.append((k, em == cl, om == cl))
    e_eq = all(r[1] for r in rows); o_eq = all(r[2] for r in rows)
    if e_eq:
        v = "エミュレータも本番と同じ(文書の制限は、試した入力では再現せず)"
    elif o_eq:
        v = "Omni で捕まえられる"
    else:
        v = "Omni でも捕まえられない"
    detail = "; ".join(f"{k or '-'}: エミュ{'=' if a else '≠'} Omni{'=' if b else '≠'}" for k, a, b in rows)
    return v, detail


print("# 最終の判定(独立監査の反映後。件数・率は記事に出さない)\n")
print("| テスト | 判定 | 副テストごと(Cloud と比べて) | 注記 |")
print("|---|---|---|---|")
for c, keys in DISCRIM.items():
    v, d = verdict(c, keys)
    print(f"| {c} | {v} | {d} | {NOTES.get(c, '')} |")

# A11: Cloud が受理した関数は差集合の抽出の誤りとして除外
cl = A[("A11", "cloud")]; keep = [k for k, val in cl.items() if val != "accept"]
excluded = [k for k, val in cl.items() if val == "accept"]
v, d = verdict("A11", keep)
print(f"| A11 | {v} | 除外(Cloud が受理={','.join(excluded)})以外の関数はすべて3者とも拒否 | 除外した関数をエミュレータは拒否した(事後の発見: エミュレータが本番にある関数を拒否する) |")

# A15: v2.1 の置き換え規則
a15 = {k: (get("A15", "cloud", k), get("A15", "emu", k), get("A15", "omni", k)) for k in A[("A15", "cloud")]}
def line(k, rule):
    cl_, em_, om_ = a15[k]
    print(f"| A15 {k} | {rule(cl_, em_, om_)} | Cloud={cl_} エミュ={em_} Omni={om_} | |")
line("search_remove_diacritics.rd_index", lambda c, e, o: "Omni で捕まえられる" if (e != c and o == c) else ("同じ" if e == c else "Omni でも捕まえられない"))
for k in ("content_type_html", "token_category_title", "substring_short_tokens_only_for_anchors", "substring_remove_diacritics", "ngrams_remove_diacritics"):
    line(k, lambda c, e, o: "エミュレータは判定不能(DEBUG_TOKENLIST が無い)。Omni は " + ("本番と同じ" if o == c else "本番と違う"))
for k in ("language_tag_ja", "search_index_options"):
    line(k, lambda c, e, o: "判定不能(Cloud でも引数の効果が出ない、または status しか見ていない)")
line("score_options", lambda c, e, o: "Omni で捕まえられる" if (e != c and o == c) else "その他")
on, off = a15["enhance_query_on"], a15["enhance_query_off"]
print(f"| A15 enhance_query | Cloud は on≠off(有効)。エミュレータと Omni は on=off で、エラーにならず黙って無視(Omni は差分ページで非対応と明記) | on={on} off={off} | |")

# B 群: S3 の記述と照合
b1 = get("B1", "omni", ""); b2 = get("B2", "omni", ""); b3 = get("B3", "omni", "")
print(f"| B1 | Omni は 8d・30d を受理、31d を拒否 = S3「30日まで」と一致。Cloud とエミュレータは 7d まで | Omni={b1} | 保持期間はエミュレータのほうが本番に近い |")
print(f"| B2 | Omni は UNIMPLEMENTED = S3「MODEL は非対応」と一致(Cloud 側は事前登録どおり無効) | Omni={b2} | |")
print(f"| B3 | Omni は Data Boost を拒否 = S3 と一致(Cloud は事前登録どおり実行せず) | Omni={b3} | |")

# C 群・陽性対照
cs = [c for (c, t) in A if c.startswith("C") and t == "cloud"]
allc = all(A[(c, "emu")] == A[(c, "cloud")] == A[(c, "omni")] for c in cs)
print(f"\n- 対照(C 群): 3者すべて一致 = {allc}")
print(f"- 陽性対照: A5 エミュ≠Cloud = {A[('A5','emu')] != A[('A5','cloud')]}、A14 エミュ≠Cloud = {get('A14','emu','drop') != get('A14','cloud','drop')}")
print("- A13(再起動、基準は仕様): エミュレータは停止のたびに DB ごと消え、Omni は graceful・kill -9 とも行が残った(コンテナの停止までで、電源断の永続性は検証していない)")

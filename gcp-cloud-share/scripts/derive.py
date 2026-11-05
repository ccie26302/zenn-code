"""Derive incremental-revenue view and market comparisons.

Inputs : data/financials.csv, data/market_share.csv
Output : data/derived.csv
Usage  : python3 -I scripts/derive.py <project_dir>

Definitions
- incr = revenue(q) - revenue(q-4)  (USD bn, YoY dollar increase)
- Microsoft comparator, two variants:
    azure : Azure revenue (FY27 definition, restated by Microsoft 2026-09). Exact where both q and q-4 restated
            amounts exist (2025Q3-). For 2024Q3-2025Q2 only the current amount is restated, so the increase is an
            ESTIMATE = rev * g/(1+g) using the growth rate reported at the time (older definition). 2024Q1-Q2: not available.
    ic    : Intelligent Cloud segment (2024Q1-2026Q2; segment abolished from 2026Q3).
- gc_share_of_incr = GC incr / (GC + AWS + Microsoft-comparator incr)
- gc_share_of_level = GC revenue / (GC + AWS + Azure revenue)  (same quarter)
- Synergy implied revenue = Synergy market size x share (Synergy row of market_share.csv). Compared with reported segment revenue:
    google vs Google Cloud segment (incl. Workspace SaaS, TPU system sales from 2026Q2, Wiz from 2026-03),
    aws vs AWS segment, microsoft vs Azure (FY27-definition restated amount; blank where not disclosed).
  Shares are published as whole percents, so implied revenue carries +/- 0.5% x market (synergy_share_rounding_band_bn).
- *_growth_minus_market_pt = company YoY growth % - Synergy market YoY growth % (pt). Azure growth is as reported at the time.
"""
import csv, os, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2", "2026Q3"]

# 2023 prior-year values (USD bn) as printed in the 2024 earnings releases (prior-year column), needed for 2024 increases.
PRIOR_2023 = {
    ("Google Cloud", "2024Q1"): 7.454, ("Google Cloud", "2024Q2"): 8.031, ("Google Cloud", "2024Q3"): 8.411, ("Google Cloud", "2024Q4"): 9.192,
    ("AWS", "2024Q1"): 21.354, ("AWS", "2024Q2"): 22.140, ("AWS", "2024Q3"): 23.059, ("AWS", "2024Q4"): 24.204,
    # Intelligent Cloud prior-year as printed in the release of each quarter (2024Q1-Q2 = FY24 structure, 2024Q3- = FY25 structure)
    ("Intelligent Cloud", "2024Q1"): 22.081, ("Intelligent Cloud", "2024Q2"): 23.993,
    ("Intelligent Cloud", "2024Q3"): 20.013, ("Intelligent Cloud", "2024Q4"): 21.525,
    ("Intelligent Cloud", "2025Q1"): 22.141, ("Intelligent Cloud", "2025Q2"): 23.785,  # FY25-structure restated prior year
}


def f(x):
    return None if x in ("", None) else float(x)


def prev(q):
    return f"{int(q[:4]) - 1}{q[4:]}"


fin = {}
for r in csv.DictReader(open(os.path.join(ROOT, "data", "financials.csv"), encoding="utf-8")):
    seg = r["segment"]
    if seg.startswith("Agents and Infra"):
        seg = "Agents and Infra"
    fin[(seg, r["calendar_quarter"])] = r

ms = {}
p = os.path.join(ROOT, "data", "market_share.csv")
if os.path.exists(p):
    for r in csv.DictReader(open(p, encoding="utf-8")):
        if r.get("source", "").lower().startswith("synergy") and f(r.get("market_size_usd_bn")):
            # keep the latest-published value per quarter if several rows exist (rows are expected in publish order)
            ms[r["calendar_quarter"]] = r


def rev(seg, q):
    r = fin.get((seg, q))
    return f(r["revenue_usd_bn"]) if r else None


def incr(seg, q):
    cur = rev(seg, q)
    if cur is None:
        return None, "na"
    if seg == "Intelligent Cloud" and q in ("2025Q1", "2025Q2", "2024Q1", "2024Q2", "2024Q3", "2024Q4"):
        return cur - PRIOR_2023[(seg, q)], "reported(prior-year column of same release)"
    pr = rev(seg, prev(q)) if (seg, q) not in PRIOR_2023 else PRIOR_2023[(seg, q)]
    if pr is not None:
        return cur - pr, "reported"
    if seg == "Azure":
        g = f(fin[(seg, q)]["yoy_growth_pct"])
        if g is not None:
            return cur * g / (100 + g), "ESTIMATE(restated rev x reported growth of older definition)"
    return None, "na"


def r2(x, nd=2):
    return "" if x is None else round(x, nd)


out_rows = []
for q in Q:
    gc, aws, az, ic = rev("Google Cloud", q), rev("AWS", q), rev("Azure", q), rev("Intelligent Cloud", q)
    gi, _ = incr("Google Cloud", q)
    ai, _ = incr("AWS", q)
    zi, zm = incr("Azure", q)
    ii, im = incr("Intelligent Cloud", q)
    row = dict(calendar_quarter=q, gc_rev_bn=gc, aws_rev_bn=aws, azure_rev_bn=az, ic_rev_bn=ic,
               gc_yoy_pct=f(fin[("Google Cloud", q)]["yoy_growth_pct"]), aws_yoy_pct=f(fin[("AWS", q)]["yoy_growth_pct"]),
               azure_yoy_pct=f(fin[("Azure", q)]["yoy_growth_pct"]),
               gc_incr_bn=r2(gi, 3), aws_incr_bn=r2(ai, 3), azure_incr_bn=r2(zi, 3), azure_incr_method=zm, ic_incr_bn=r2(ii, 3))
    row["gc_share_of_incr_azure_basis_pct"] = r2(gi / (gi + ai + zi) * 100, 1) if None not in (gi, ai, zi) else ""
    row["gc_share_of_incr_ic_basis_pct"] = r2(gi / (gi + ai + ii) * 100, 1) if None not in (gi, ai, ii) else ""
    row["aws_share_of_incr_azure_basis_pct"] = r2(ai / (gi + ai + zi) * 100, 1) if None not in (gi, ai, zi) else ""
    row["azure_share_of_incr_azure_basis_pct"] = r2(zi / (gi + ai + zi) * 100, 1) if None not in (gi, ai, zi) else ""
    row["gc_share_of_rev_level_azure_basis_pct"] = r2(gc / (gc + aws + az) * 100, 1) if None not in (gc, aws, az) else ""
    row["gc_incr_per_aws_incr"] = r2(gi / ai, 2) if None not in (gi, ai) else ""
    # Synergy comparisons
    m = ms.get(q)
    if m:
        mkt, mg = f(m["market_size_usd_bn"]), f(m.get("market_yoy_growth_pct"))
        row["synergy_market_bn"], row["synergy_market_yoy_pct"] = mkt, mg
        row["synergy_share_rounding_band_bn"] = r2(mkt * 0.005, 2)  # shares are whole %, so implied rev is +/- this
        for key, seg_rev, yoy in (("google", gc, row["gc_yoy_pct"]), ("aws", aws, row["aws_yoy_pct"]), ("microsoft", az, row["azure_yoy_pct"])):
            sh = f(m.get(f"{key}_share_pct"))
            imp = mkt * sh / 100 if (mkt and sh is not None) else None
            row[f"synergy_implied_{key}_bn"] = r2(imp, 1)
            row[f"{key}_segment_minus_implied_bn"] = r2(seg_rev - imp, 1) if None not in (seg_rev, imp) else ""
            row[f"{key}_growth_minus_market_pt"] = r2(yoy - mg, 1) if None not in (yoy, mg) else ""
    out_rows.append(row)

notes = {
    "2024Q1": "Azure金額非開示のためAzure基準のシェア計算不可。IC基準のみ(IC=FY24旧構造)",
    "2024Q2": "同上",
    "2024Q3": "Azure増収額は推計(再表示後の当期額×当時定義の成長率)",
    "2024Q4": "Azure増収額は推計",
    "2025Q1": "Azure増収額は推計",
    "2025Q2": "Azure増収額は推計",
    "2026Q3": "Intelligent Cloud廃止のためIC基準なし。Google Cloud増収にはTPU system sales(額非開示)とWiz連結(額非開示)を含む",
    "2026Q1": "Google CloudにWiz連結開始(2026-03-11〜、額非開示)",
    "2026Q2": "Google CloudにTPU system sales計上開始(額非開示)、Wiz連結",
}
cols = ["calendar_quarter", "gc_rev_bn", "aws_rev_bn", "azure_rev_bn", "ic_rev_bn", "gc_yoy_pct", "aws_yoy_pct", "azure_yoy_pct",
        "gc_incr_bn", "aws_incr_bn", "azure_incr_bn", "azure_incr_method", "ic_incr_bn",
        "gc_share_of_incr_azure_basis_pct", "aws_share_of_incr_azure_basis_pct", "azure_share_of_incr_azure_basis_pct",
        "gc_share_of_incr_ic_basis_pct", "gc_share_of_rev_level_azure_basis_pct", "gc_incr_per_aws_incr",
        "synergy_market_bn", "synergy_market_yoy_pct", "synergy_share_rounding_band_bn",
        "gc_growth_minus_market_pt", "aws_growth_minus_market_pt", "microsoft_growth_minus_market_pt",
        "synergy_implied_google_bn", "google_segment_minus_implied_bn",
        "synergy_implied_aws_bn", "aws_segment_minus_implied_bn",
        "synergy_implied_microsoft_bn", "microsoft_segment_minus_implied_bn", "note"]
for r in out_rows:
    r["note"] = notes.get(r["calendar_quarter"], "")
    if "gc_growth_minus_market_pt" not in r and "google_growth_minus_market_pt" in r:
        pass
    r["gc_growth_minus_market_pt"] = r.pop("google_growth_minus_market_pt", "")
with open(os.path.join(ROOT, "data", "derived.csv"), "w", newline="", encoding="utf-8") as fo:
    w = csv.DictWriter(fo, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in out_rows:
        w.writerow({c: ("" if r.get(c) is None else r.get(c, "")) for c in cols})
print("wrote data/derived.csv")
for r in out_rows:
    print(r["calendar_quarter"], "GC+%s AWS+%s Az+%s(%s) IC+%s | GC share(Az)=%s%% (IC)=%s%% level=%s%%" % (
        r["gc_incr_bn"], r["aws_incr_bn"], r["azure_incr_bn"], r["azure_incr_method"][:8], r["ic_incr_bn"],
        r["gc_share_of_incr_azure_basis_pct"], r["gc_share_of_incr_ic_basis_pct"], r["gc_share_of_rev_level_azure_basis_pct"]))

#!/usr/bin/env python3
"""記事用のグラフ2枚を作る。入力: data/derived.csv、出力: ~/zenn-content/images/cloudshare-*.png"""
import csv, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path.home() / "zenn-content" / "images"
font_manager.fontManager.addfont("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc")
plt.rcParams["font.family"] = "Hiragino Sans"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

rows = list(csv.DictReader(open(ROOT / "data" / "derived.csv")))
def series(key, start=None):
    out = []
    for r in rows:
        if start and r["calendar_quarter"] < start:
            continue
        v = r[key]
        out.append((r["calendar_quarter"], float(v) if v not in ("", None) else None))
    return out

C_G, C_A, C_M, C_K = "#2a6fdb", "#e07a1f", "#2f9e6e", "#666666"
lab = lambda q: q.replace("Q", "\nQ")

# 1. 3社の増収額に占める Google Cloud の割合と、売上規模に占める割合
s1 = series("gc_share_of_incr_azure_basis_pct", "2024Q3")
s2 = series("gc_share_of_rev_level_azure_basis_pct", "2024Q3")
fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
x = range(len(s1))
ax.plot(x, [v for _, v in s1], color=C_G, lw=2.5, marker="o", label="増えた売上に占める割合")
ax.plot(x, [v for _, v in s2], color=C_K, lw=1.8, ls="--", marker="o", ms=4, label="売上の規模に占める割合")
for i, (_, v) in enumerate(s1):
    if i in (0, len(s1) - 1):
        ax.annotate(f"{v:.1f}%", (i, v), textcoords="offset points", xytext=(0, 8), ha="center", color=C_G, fontsize=10)
qs = [q for q, _ in s1]
for q, txt in (("2026Q1", "Wiz を\n連結"), ("2026Q2", "TPU の機械\n販売を計上")):
    i = qs.index(q)
    ax.axvline(i, color="#999", lw=0.8, ls=":")
    ax.text(i + 0.08, 1.5, txt, fontsize=8, color="#555", va="bottom")
ax.set_xticks(list(x)); ax.set_xticklabels([lab(q) for q, _ in s1], fontsize=9)
ax.set_ylabel("%"); ax.set_ylim(0, 45); ax.grid(axis="y", alpha=0.3)
ax.set_title("Google Cloud・AWS・Azure の3社のうち、Google Cloud が占める割合", fontsize=12)
ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.text(0.01, 0.01, "出典: 各社の決算書類(SEC)から計算。増えた売上は前年同期比。Azure は開示の成長率から算出した期を含む。\nGoogle Cloud は Workspace、2026年1〜3月期からの Wiz、4〜6月期からの TPU 販売を含む", fontsize=7, color="#555")
fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(OUT / "cloudshare-incremental-share.png"); plt.close(fig)

# 2. 各社の売上の伸び率と、市場全体の伸び率
g = series("gc_yoy_pct"); a = series("aws_yoy_pct"); m = series("azure_yoy_pct"); mk = series("synergy_market_yoy_pct")
# Synergy の市場規模 × Google のシェアで推計した、インフラだけの売上の伸び率(前年同期比)
ms = {r["calendar_quarter"]: r for r in csv.DictReader(open(ROOT / "data" / "market_share.csv")) if r["source"] == "Synergy"}
def implied(q):
    r = ms.get(q)
    return float(r["market_size_usd_bn"]) * float(r["google_share_pct"]) / 100 if r and r["market_size_usd_bn"] and r["google_share_pct"] else None
gi = []
for q, _ in g:
    y, n = int(q[:4]), q[4:]
    cur, prev = implied(q), implied(f"{y-1}{n}")
    gi.append((q, 100 * (cur / prev - 1) if cur and prev else None))
fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
x = range(len(g))
ax.plot(x, [v for _, v in mk], color=C_K, lw=6, alpha=0.25, label="市場全体(Synergy)")
ax.plot(x, [v for _, v in g], color=C_G, lw=2.5, marker="o", label="Google Cloud(決算)")
ax.plot(x, [v for _, v in gi], color=C_G, lw=1.6, ls=":", marker="s", ms=3, label="Google(インフラだけの推計)")
ax.plot(x, [v for _, v in m], color=C_M, lw=2, marker="o", ms=4, label="Azure")
ax.plot(x, [v for _, v in a], color=C_A, lw=2, marker="o", ms=4, label="AWS")
for s, c in ((g, C_G), (gi, C_G), (m, C_M), (a, C_A), (mk, C_K)):
    q, v = s[-1]
    ax.annotate(f"{v:.0f}%", (len(s) - 1, v), textcoords="offset points", xytext=(8, -3), color=c, fontsize=9)
ax.set_xticks(list(x)); ax.set_xticklabels([lab(q) for q, _ in g], fontsize=8)
ax.set_ylabel("前年同期比 %"); ax.grid(axis="y", alpha=0.3)
ax.set_title("売上の伸び率と、クラウドインフラ市場全体の伸び率", fontsize=12)
ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.text(0.01, 0.01, "出典: 各社の決算書類(SEC)、Synergy Research Group。市場の伸びは一部の期で為替の影響を除いた値。\nGoogle Cloud(決算)は Workspace と TPU 販売を含む。点線は Synergy の市場規模 × シェアからの推計で、シェアの丸めにより幅がある", fontsize=7, color="#555")
fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(OUT / "cloudshare-growth-vs-market.png"); plt.close(fig)
print("ok")

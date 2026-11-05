"""Build data/financials.csv from values hand-extracted from SEC filings (8-K Ex.99.1 / 10-Q / 10-K).

All $ values in USD millions in this file; the CSV is written in USD billions.
Raw text of every filing used is in raw/ (fetched by scripts/fetch_sec.py), so each value can be re-checked
with e.g.  grep -n "Google Cloud |" raw/GOOGL_8-K_2026-10-28_2026-10-28.txt

Usage: python3 -I scripts/build_financials.py <project_dir>
"""
import csv, os, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = "https://www.sec.gov/Archives/edgar/data/"
Q = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2", "2026Q3"]

# ---------------------------------------------------------------- Alphabet / Google Cloud
G_URL = {  # earnings release (8-K Ex.99.1) and 10-Q/10-K for each quarter
    "2024Q1": ("000165204424000047/googexhibit991q12024.htm", "000165204424000053/goog-20240331.htm"),
    "2024Q2": ("000165204424000076/googexhibit991q22024.htm", "000165204424000079/goog-20240630.htm"),
    "2024Q3": ("000165204424000115/googexhibit991q32024.htm", "000165204424000118/goog-20240930.htm"),
    "2024Q4": ("000165204425000010/googexhibit991q42024.htm", "000165204425000014/goog-20241231.htm"),
    "2025Q1": ("000165204425000040/googexhibit991q12025.htm", "000165204425000043/goog-20250331.htm"),
    "2025Q2": ("000165204425000056/googexhibit991q22025.htm", "000165204425000062/goog-20250630.htm"),
    "2025Q3": ("000165204425000087/googexhibit991q32025.htm", "000165204425000091/goog-20250930.htm"),
    "2025Q4": ("000165204426000012/googexhibit991q42025.htm", "000165204426000018/goog-20251231.htm"),
    "2026Q1": ("000165204426000043/googexhibit991q12026.htm", "000165204426000048/goog-20260331.htm"),
    "2026Q2": ("000165204426000066/googexhibit991q22026.htm", "000165204426000071/goog-20260630.htm"),
    "2026Q3": ("000165204426000080/googexhibit991q32026.htm", "000165204426000084/goog-20260930.htm"),
}
# quarter: (revenue, prior-year revenue as shown in same release, operating income, backlog $bn, capex(purchases of PP&E))
GC = {
    "2024Q1": (9574, 7454, 900, 72.5, 12012),
    "2024Q2": (10347, 8031, 1172, 78.8, 13186),
    "2024Q3": (11353, 8411, 1947, 86.8, 13061),
    "2024Q4": (11955, 9192, 2093, 93.2, 14276),
    "2025Q1": (12260, 9574, 2177, 92.4, 17197),
    "2025Q2": (13624, 10347, 2826, 108.2, 22446),
    "2025Q3": (15157, 11353, 3594, 157.7, 23953),
    "2025Q4": (17664, 11955, 5313, 242.8, 27851),
    "2026Q1": (20028, 12260, 6598, 462.3, 35674),
    "2026Q2": (24768, 13624, 8814, 513.9, 44924),
    "2026Q3": (30709, 15157, 11121, 560.8, 51355),
}
GC_NOTE = {
    "2024Q1": "backlog=Alphabet全体のRPO(10-Qでは'primarily related to Google Cloud')。1年以内契約は除外の旧定義",
    "2024Q2": "backlog=Alphabet全体RPO(primarily Google Cloud)、旧定義",
    "2024Q3": "backlog=Alphabet全体RPO(primarily Google Cloud)、旧定義",
    "2024Q4": "backlog=Alphabet全体RPO(primarily Google Cloud)、旧定義(10-K)",
    "2025Q1": "backlog=Alphabet全体RPO(primarily Google Cloud)、旧定義",
    "2025Q2": "backlog=Alphabet全体RPO(primarily Google Cloud)、旧定義",
    "2025Q3": "backlog=Alphabet全体RPO(primarily Google Cloud)、旧定義",
    "2025Q4": "backlog=Alphabet全体RPO(primarily Google Cloud)、旧定義(10-K)",
    "2026Q1": "backlog=Google Cloud分(全体467.6)。2026Q1から1年以内契約も含める定義に変更→前期以前と不連続。2026-03-11にWiz買収完了(295億ドル)、以後Google Cloudセグメントに連結(Wizの売上寄与額は非開示)",
    "2026Q2": "backlog=Google Cloud分(全体519.5)。10-Q:'in the second quarter of 2026, we began recognizing revenue from the sale of TPU systems'、TPU売上額は非開示。Wiz連結含む",
    "2026Q3": "backlog=Google Cloud分(全体567.7、うちCrux AI(持分法JV・関連当事者)向け16.8)。増収156億ドルの主因は10-QでGCPとTPU system salesと記載、TPU売上額・比率は非開示。Wiz連結含む",
}

# ---------------------------------------------------------------- Amazon / AWS
A_URL = {
    "2024Q1": ("1018724/000101872424000081/amzn-20240331xex991.htm", "1018724/000101872424000083/amzn-20240331.htm"),
    "2024Q2": ("1018724/000101872424000128/amzn-20240630xex991.htm", "1018724/000101872424000130/amzn-20240630.htm"),
    "2024Q3": ("1018724/000101872424000158/amzn-20240930xex991.htm", "1018724/000101872424000161/amzn-20240930.htm"),
    "2024Q4": ("1018724/000101872425000002/amzn-20241231xex991.htm", "1018724/000101872425000004/amzn-20241231.htm"),
    "2025Q1": ("1018724/000101872425000034/amzn-20250331xex991.htm", "1018724/000101872425000036/amzn-20250331.htm"),
    "2025Q2": ("1018724/000101872425000084/amzn-20250630xex991.htm", "1018724/000101872425000086/amzn-20250630.htm"),
    "2025Q3": ("1018724/000101872425000121/amzn-20250930xex991.htm", "1018724/000101872425000123/amzn-20250930.htm"),
    "2025Q4": ("1018724/000101872426000002/amzn-20251231xex991.htm", "1018724/000101872426000004/amzn-20251231.htm"),
    "2026Q1": ("1018724/000101872426000012/amzn-20260331xex991.htm", "1018724/000101872426000014/amzn-20260331.htm"),
    "2026Q2": ("1018724/000101872426000024/amzn-20260630xex991.htm", "1018724/000101872426000026/amzn-20260630.htm"),
    "2026Q3": ("1018724/000101872426000038/amzn-20260930xex991.htm", "1018724/000101872426000040/amzn-20260930.htm"),
}
# (revenue, prior-year revenue, operating income, backlog $bn (company-wide, >1yr contracts), capex = purchases of PP&E (gross))
AWS = {
    "2024Q1": (25037, 21354, 9421, 157.7, 14925),
    "2024Q2": (26281, 22140, 9334, 156.6, 17620),
    "2024Q3": (27452, 23059, 10447, 164, 22620),
    "2024Q4": (28786, 24204, 10632, 177, 27834),
    "2025Q1": (29267, 25037, 11547, 189, 25019),
    "2025Q2": (30873, 26281, 10160, 195, 32183),
    "2025Q3": (33006, 27452, 11434, 200, 35095),
    "2025Q4": (35579, 28786, 12465, 244, 39522),
    "2026Q1": (37587, 29267, 14161, 364, 44203),
    "2026Q2": (42232, 30873, 16621, 496, 54208),
    "2026Q3": (45984, 33006, 17773, 578, 77259),
}
AWS_NOTE_COMMON = ("backlog=Amazon全体の未認識契約額(10-Q:'primarily related to AWS'、当初期間1年超の契約のみ、'approximately'表記の期あり)。"
                   "capex=キャッシュフロー計算書のPurchases of property and equipment(総額、売却・インセンティブ控除前)")
AWS_NOTE = {
    "2025Q2": "Amazonの決算資料はAWS成長率を17.5%と記載",
    "2026Q1": "残存期間の加重平均が4.1年→5.5年に伸長(長期契約の増加)",
    "2026Q2": "加重平均残存期間6.4年",
    "2026Q3": "加重平均残存期間6.1年。CEOコメントでAWS年換算ランレート1840億ドル",
}

# ---------------------------------------------------------------- Microsoft
# Calendar mapping: FY ends June 30. CY Q3 = FY Q1, CY Q4 = FY Q2, CY Q1 = FY Q3, CY Q2 = FY Q4.
M_URL = {
    "2024Q1": ("789019/000095017024048268/msft-ex99_1.htm", "789019/000095017024048288/msft-20240331.htm", "FY24Q3"),
    "2024Q2": ("789019/000095017024087835/msft-ex99_1.htm", "789019/000095017024087843/msft-20240630.htm", "FY24Q4"),
    "2024Q3": ("789019/000095017024118955/msft-ex99_1.htm", "789019/000095017024118967/msft-20240930.htm", "FY25Q1"),
    "2024Q4": ("789019/000095017025010484/msft-ex99_1.htm", "789019/000095017025010491/msft-20241231.htm", "FY25Q2"),
    "2025Q1": ("789019/000095017025061032/msft-ex99_1.htm", "789019/000095017025061046/msft-20250331.htm", "FY25Q3"),
    "2025Q2": ("789019/000095017025100226/msft-ex99_1.htm", "789019/000095017025100235/msft-20250630.htm", "FY25Q4"),
    "2025Q3": ("789019/000119312525256310/msft-ex99_1.htm", "789019/000119312525256321/msft-20250930.htm", "FY26Q1"),
    "2025Q4": ("789019/000119312526027198/msft-ex99_1.htm", "789019/000119312526027207/msft-20251231.htm", "FY26Q2"),
    "2026Q1": ("789019/000119312526191457/msft-ex99_1.htm", "789019/000119312526191507/msft-20260331.htm", "FY26Q3"),
    "2026Q2": ("789019/000119312526323632/msft-ex99_1.htm", "789019/000119312526323660/msft-20260630.htm", "FY26Q4"),
    "2026Q3": ("789019/000119312526436122/msft-ex99_1.htm", "789019/000119312526436133/msft-20260930.htm", "FY27Q1"),
}
M_RECAST_2026 = SEC + "789019/000119312526380280/d291965dex991.htm"  # 8-K 2026-09-02 "FY27 Segments and Investor Metrics"
M_RECAST_2024 = SEC + "789019/000119312524204403/d846847dex991.htm"  # 8-K 2024-08-21 FY25 segment changes
# Intelligent Cloud: (revenue, prior-year revenue, op income) as in the release of that quarter
IC = {
    "2024Q1": (26708, 22081, 12513, "FY24構造(旧)。2024-08にEMS/Power BI等をPBPへ移す再編があり、FY25構造の再表示値は22,141"),
    "2024Q2": (28515, 23993, 12859, "FY24構造(旧)。FY25構造の再表示値は23,785"),
    "2024Q3": (24092, 20013, 10503, "FY25構造(2024-08再編後)"),
    "2024Q4": (25544, 21525, 10851, "FY25構造"),
    "2025Q1": (26751, 22141, 11095, "FY25構造"),
    "2025Q2": (29878, 23785, 12140, "FY25構造"),
    "2025Q3": (30897, 24092, 13391, "FY26構造(=FY25構造)"),
    "2025Q4": (32907, 25544, 13873, ""),
    "2026Q1": (34681, 26751, 13753, ""),
    "2026Q2": (39306, 29878, 15955, "FY26最後のIntelligent Cloud。FY27(2026Q3〜)でセグメント廃止"),
}
# Azure: restated $ (FY27 definition; 8-K 2026-09-02 + FY27Q1 release), reported growth (GAAP%, definition of that time)
AZ = {
    "2024Q1": (None, 31, "金額非開示。成長率は当時定義(Azure and other cloud services)。2024-08の定義変更後の再表示値は35%"),
    "2024Q2": (None, 29, "金額非開示。当時定義29%(恒常為替30%)。2024-08再表示値は34%(恒常為替35%)"),
    "2024Q3": (16021, 33, "金額は2026-09の再表示値(FY27定義:GitHub/Security Copilot/HLSを除外)。成長率は当時定義(FY25定義)の報告値で、FY27定義の前年金額は非開示"),
    "2024Q4": (17337, 31, "金額=FY27定義の再表示値、成長率=当時定義"),
    "2025Q1": (18540, 33, "金額=FY27定義の再表示値、成長率=当時定義(恒常為替35%)"),
    "2025Q2": (20712, 39, "金額=FY27定義の再表示値、成長率=当時定義。FY25通期でAzureは'surpassed $75 billion, up 34%'(当時定義)、FY27定義の再表示通期は72,610"),
    "2025Q3": (22384, 40, "金額=FY27定義の再表示値。成長率は当時定義40%、FY27定義の再表示も40%"),
    "2025Q4": (24129, 39, "当時定義39%、FY27定義再表示39%"),
    "2026Q1": (26008, 40, "当時定義40%、FY27定義再表示40%"),
    "2026Q2": (29417, 43, "当時定義43%、FY27定義再表示42%。FY26通期でAzure初の1000億ドル超(FY27定義101,938)"),
    "2026Q3": (33165, 48, "FY27定義で初めて四半期のAzure売上額を決算資料で開示"),
}
MCLOUD = {  # Microsoft Cloud revenue $bn, growth %
    "2024Q1": (35.1, 23), "2024Q2": (36.8, None), "2024Q3": (38.9, 22), "2024Q4": (40.9, 21),
    "2025Q1": (42.4, 20), "2025Q2": (46.7, 27), "2025Q3": (49.1, 26), "2025Q4": (51.5, 26),
    "2026Q1": (54.5, 29), "2026Q2": (59.3, 27), "2026Q3": (63.9, 30),
}
CRPO = {"2024Q1": 235, "2024Q2": 269, "2024Q3": 259, "2024Q4": 298, "2025Q1": 315, "2025Q2": 368,
        "2025Q3": 392, "2025Q4": 625, "2026Q1": 627, "2026Q2": 678, "2026Q3": 677}
M_CAPEX = {"2024Q1": 10952, "2024Q2": 13873, "2024Q3": 14923, "2024Q4": 15804, "2025Q1": 16745, "2025Q2": 17079,
           "2025Q3": 19394, "2025Q4": 29876, "2026Q1": 30876, "2026Q2": 35802, "2026Q3": 39367}

# ---------------------------------------------------------------- Oracle (FY ends May 31; quarters are offset by one month)
O = [  # calendar_quarter(approx), fiscal, OCI revenue $mn or None, growth %, RPO $bn, capex quarterly $mn (YTD differences), url
    ("2024Q1", "FY24Q3(2023-12〜2024-02)", 1800, 49, 80, None, "1341439/000095017024029250/orcl-ex99_1.htm"),
    ("2024Q2", "FY24Q4(2024-03〜05)", 2000, 42, 98, None, "1341439/000095017024071916/orcl-ex99_1.htm"),
    ("2024Q3", "FY25Q1(2024-06〜08)", 2154, 45, 99, 2303, "1341439/000095017024104753/orcl-ex99_1.htm"),
    ("2024Q4", "FY25Q2(2024-09〜11)", 2434, 52, 97, 3970, "1341439/000095017024134537/orcl-ex99_1.htm"),
    ("2025Q1", "FY25Q3(2024-12〜2025-02)", 2652, 49, 130, 5862, "1341439/000095017025036295/orcl-ex99_1.htm"),
    ("2025Q2", "FY25Q4(2025-03〜05)", 2995, 52, 138, 9080, "1341439/000095017025084831/orcl-ex99_1.htm"),
    ("2025Q3", "FY26Q1(2025-06〜08)", 3347, 55, 455, 8502, "1341439/000119312525199175/orcl-ex99_1.htm"),
    ("2025Q4", "FY26Q2(2025-09〜11)", 4079, 68, 523, 12033, "1341439/000119312525314207/orcl-ex99_1.htm"),
    ("2026Q1", "FY26Q3(2025-12〜2026-02)", 4888, 84, 553, 18635, "1341439/000119312526100148/orcl-ex99_1.htm"),
    ("2026Q2", "FY26Q4(2026-03〜05)", 5787, 93, 638, 16493, "1341439/000119312526265848/orcl-ex99_1.htm"),
    ("2026Q3", "FY27Q1(2026-06〜08)", 7388, 121, 664, 28499, "1341439/000119312526387905/orcl-ex99_1.htm"),
]


def bn(x, nd=3):
    return "" if x is None else round(x / 1000.0, nd)


def pct(a, b):
    return round((a / b - 1) * 100, 1)


rows = []
for q in Q:
    r, p, oi, bl, cx = GC[q]
    rel, tenq = G_URL[q]
    rows.append(dict(company="Alphabet", calendar_quarter=q, segment="Google Cloud", revenue_usd_bn=bn(r),
                     yoy_growth_pct=pct(r, p), operating_income_usd_bn=bn(oi), operating_margin_pct=round(oi / r * 100, 1),
                     backlog_usd_bn=bl, capex_usd_bn=bn(cx),
                     source_url=f"{SEC}1652044/{rel} ; {SEC}1652044/{tenq}",
                     note=f"前年同期売上{bn(p)}(同リリース記載)。capex=Alphabet全体のPurchases of property and equipment。" + GC_NOTE[q]))
for q in Q:
    r, p, oi, bl, cx = AWS[q]
    rel, tenq = A_URL[q]
    rows.append(dict(company="Amazon", calendar_quarter=q, segment="AWS", revenue_usd_bn=bn(r), yoy_growth_pct=pct(r, p),
                     operating_income_usd_bn=bn(oi), operating_margin_pct=round(oi / r * 100, 1), backlog_usd_bn=bl,
                     capex_usd_bn=bn(cx), source_url=f"{SEC}{rel} ; {SEC}{tenq}",
                     note=f"前年同期売上{bn(p)}。" + AWS_NOTE_COMMON + ("。" + AWS_NOTE[q] if q in AWS_NOTE else "")))
for q in Q:
    rel, tenq, fy = M_URL[q]
    src = f"{SEC}{rel} ; {SEC}{tenq}"
    if q in IC:
        r, p, oi, n = IC[q]
        rows.append(dict(company="Microsoft", calendar_quarter=q, segment="Intelligent Cloud", revenue_usd_bn=bn(r),
                         yoy_growth_pct=pct(r, p), operating_income_usd_bn=bn(oi), operating_margin_pct=round(oi / r * 100, 1),
                         backlog_usd_bn=CRPO[q], capex_usd_bn=bn(M_CAPEX[q]),
                         source_url=src + (f" ; {M_RECAST_2026}" if q >= "2024Q3" else ""),
                         note=f"{fy}。前年同期{bn(p)}(同リリース記載)。backlog=commercial RPO(Microsoft全体の商用分、Intelligent Cloud単独ではない)。capex=Additions to property and equipment(現金、ファイナンスリース含まず)。{n}"))
    else:
        rows.append(dict(company="Microsoft", calendar_quarter=q, segment="Agents and Infra (Intelligent Cloudの後継ではない)",
                         revenue_usd_bn=76.795, yoy_growth_pct=pct(76795, 61672), operating_income_usd_bn=40.558,
                         operating_margin_pct=round(40558 / 76795 * 100, 1), backlog_usd_bn=CRPO[q], capex_usd_bn=bn(M_CAPEX[q]),
                         source_url=src + f" ; {M_RECAST_2026}",
                         note=f"{fy}。FY27からセグメントがAgents and Infra/Devices and Consumerの2つに再編、Intelligent Cloudは廃止。Agents and InfraはAzure+M365 cloud+業種別+ライセンス等を含み、IC/AWS/Google Cloudとは比較不能。前年同期は再表示値61.672"))
    az, g, n = AZ[q]
    rows.append(dict(company="Microsoft", calendar_quarter=q, segment="Azure", revenue_usd_bn=bn(az), yoy_growth_pct=g,
                     operating_income_usd_bn="", operating_margin_pct="", backlog_usd_bn="", capex_usd_bn="",
                     source_url=src + (f" ; {M_RECAST_2026}" if az else (f" ; {M_RECAST_2024}" if q < "2024Q3" else "")),
                     note=f"{fy}。Azure単体の営業利益は非開示。{n}"))
    mc, mg = MCLOUD[q]
    rows.append(dict(company="Microsoft", calendar_quarter=q, segment="Microsoft Cloud", revenue_usd_bn=mc,
                     yoy_growth_pct="" if mg is None else mg, operating_income_usd_bn="", operating_margin_pct="",
                     backlog_usd_bn=CRPO[q], capex_usd_bn="", source_url=src,
                     note=(f"{fy}。Azure+M365商用クラウド+Dynamics等のSaaSを含む(SaaS比率が高くIaaS/PaaS比較には不向き)。"
                           + ("四半期値は決算リリースに記載なし。FY24通期137.4(10-K)−FY24Q1〜Q3(31.8/33.7/35.1、各10-Q)から逆算した値。成長率は一次資料で未確認" if q == "2024Q2" else "")
                           + ("FY27定義(Industry solutions cloud含む)" if q == "2026Q3" else ""))))
for q, fy, rv, g, rpo, cx, u in O:
    rows.append(dict(company="Oracle", calendar_quarter=q, segment="Oracle Cloud Infrastructure (IaaS)", revenue_usd_bn=bn(rv),
                     yoy_growth_pct=g, operating_income_usd_bn="", operating_margin_pct="", backlog_usd_bn=rpo,
                     capex_usd_bn=bn(cx), source_url=SEC + u,
                     note=(f"{fy}。会計年度が5月末締めのため暦年四半期と1か月ずれる(最も重なる暦四半期に割当)。OCI営業利益は非開示。"
                           "backlog=Oracle全体のRPO。capexは累計値の差分で算出した四半期値。"
                           + ("売上はリリース見出しの丸め値($1.8B/$2.0B)。" if rv in (1800, 2000) else "")
                           + ("capexは本データ未取得。" if cx is None else ""))))

out = os.path.join(ROOT, "data", "financials.csv")
cols = ["company", "calendar_quarter", "segment", "revenue_usd_bn", "yoy_growth_pct", "operating_income_usd_bn",
        "operating_margin_pct", "backlog_usd_bn", "capex_usd_bn", "source_url", "note"]
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow(r)
print(f"wrote {len(rows)} rows -> {out}")

"""Fetch earnings 8-K Exhibit 99.1 and 10-Q/10-K primary docs from SEC EDGAR, save as text.
Usage: python3 -I fetch_sec.py <raw_dir>
"""
import json, sys, os, re, time, urllib.request, html
RAW = sys.argv[1]
UA = {"User-Agent": "YOUR_NAME your-email@example.com"}
CIKS = {"GOOGL": "1652044", "AMZN": "1018724", "MSFT": "789019", "ORCL": "1341439"}
def get(url):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception as e:
            time.sleep(2)
    raise RuntimeError(url)
def to_text(b):
    s = b.decode("utf-8", "ignore")
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", s)
    s = re.sub(r"(?i)</td>|</th>", " | ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s
manifest = []
for t, cik in CIKS.items():
    d = json.load(open(os.path.join(RAW, f"sub_{t}.json")))
    r = d["filings"]["recent"]
    for i in range(len(r["form"])):
        f, fd = r["form"][i], r["filingDate"][i]
        if fd < "2024-04-01": continue
        is8k = f == "8-K" and "2.02" in r["items"][i]
        if not (is8k or f in ("10-Q", "10-K")): continue
        acc = r["accessionNumber"][i].replace("-", "")
        base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/"
        if is8k:
            idx = json.loads(get(base + "index.json"))
            names = [x["name"] for x in idx["directory"]["item"]]
            ex = [n for n in names if re.search(r"(?i)ex(hibit)?-?99[._-]?1|ex991|ex-991", n) and n.endswith(".htm")]
            if not ex:
                ex = [n for n in names if "99" in n and n.endswith(".htm")]
            doc = ex[0] if ex else r["primaryDocument"][i]
        else:
            doc = r["primaryDocument"][i]
        url = base + doc
        out = os.path.join(RAW, f"{t}_{f}_{r['reportDate'][i]}_{fd}.txt")
        if not os.path.exists(out):
            open(out, "w").write(to_text(get(url)))
            time.sleep(0.3)
        manifest.append({"ticker": t, "form": f, "filed": fd, "period": r["reportDate"][i], "url": url, "file": os.path.basename(out)})
        print(t, f, fd, url)
json.dump(manifest, open(os.path.join(RAW, "manifest.json"), "w"), indent=1)

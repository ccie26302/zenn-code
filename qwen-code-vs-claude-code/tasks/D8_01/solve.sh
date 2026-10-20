cd "$1" && python3 - <<'PY'
import json, os
from bs4 import BeautifulSoup
out = open("products.jsonl", "w", encoding="utf-8"); page = "index.html"
while page:
    s = BeautifulSoup(open(os.path.join("site", page), encoding="utf-8"), "html.parser")
    for c in s.select("div.card"):
        if c.select_one(".sku") is None: continue
        out.write(json.dumps({"sku": c.select_one(".sku").text, "name": c.select_one(".title").text, "price": int(c.select_one(".price").text.replace(",", "").replace("円", "")),
                              "in_stock": c.select_one(".stock").text == "在庫あり"}, ensure_ascii=False) + "\n")
    n = s.select_one("a.next"); page = n["href"] if n else None
PY

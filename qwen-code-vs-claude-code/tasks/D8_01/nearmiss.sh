# 惜しい誤答: 1ページ目だけを抜き出す
cd "$1" && python3 - <<'PY'
import json
from bs4 import BeautifulSoup
s = BeautifulSoup(open("site/index.html", encoding="utf-8"), "html.parser"); out = open("products.jsonl", "w", encoding="utf-8")
for c in s.select("div.card"):
    if c.select_one(".sku") is None: continue
    out.write(json.dumps({"sku": c.select_one(".sku").text, "name": c.select_one(".title").text, "price": int(c.select_one(".price").text.replace(",", "").replace("円", "")), "in_stock": c.select_one(".stock").text == "在庫あり"}, ensure_ascii=False) + "\n")
PY

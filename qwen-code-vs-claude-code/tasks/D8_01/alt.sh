# 別解: 正規表現で全ページを読む
cd "$1" && python3 - <<'PY'
import glob, json, re
def key(f): return 1 if f.endswith("index.html") else int(re.search(r"page(\d+)", f).group(1))
out = open("products.jsonl", "w", encoding="utf-8")
for f in sorted(glob.glob("site/*.html"), key=key):
    for sku, name, price, stock in re.findall(r'<span class="sku">(.*?)</span><h3 class="title">(.*?)</h3><p class="price">(.*?)</p><p class="stock">(.*?)</p>', open(f, encoding="utf-8").read()):
        out.write(json.dumps({"sku": sku, "name": name, "price": int(price.replace(",", "").replace("円", "")), "in_stock": stock == "在庫あり"}, ensure_ascii=False) + "\n")
PY

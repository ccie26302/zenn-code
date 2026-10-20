import os, random, sys
def gen():
    rnd = random.Random(1808); items = []
    for i in range(1, 38):
        items.append({"sku": "QX-%03d" % (i * 3), "name": rnd.choice(["USB-C ケーブル", "モバイルバッテリー", "ノートPCスタンド", "Webカメラ", "マイク"]) + " %s" % rnd.choice(["Lite", "Pro", "Max", "Mini"]),
                      "price": rnd.choice([980, 1480, 2980, 4980, 12800, 19800]), "in_stock": rnd.random() > 0.3})
    return items
if __name__ == "__main__":
    d = os.path.join(sys.argv[1], "site"); os.makedirs(d); items = gen(); per = 10; pages = [items[i:i + per] for i in range(0, len(items), per)]
    for n, pg in enumerate(pages):
        cards = "".join('<div class="card"><span class="sku">%s</span><h3 class="title">%s</h3><p class="price">%s円</p><p class="stock">%s</p></div>\n'
                        % (it["sku"], it["name"], "{:,}".format(it["price"]), "在庫あり" if it["in_stock"] else "在庫切れ") for it in pg)
        nav = ('<a class="next" href="page%d.html">次へ</a>' % (n + 2)) if n + 1 < len(pages) else ""
        ad = '<div class="card ad"><h3 class="title">広告: 今だけ送料無料</h3></div>' if n == 1 else ""
        open(os.path.join(d, "index.html" if n == 0 else "page%d.html" % (n + 1)), "w", encoding="utf-8").write(
            "<!doctype html><html><head><meta charset='utf-8'><title>商品一覧 %d</title></head><body>%s%s<nav>%s</nav></body></html>" % (n + 1, cards, ad, nav))

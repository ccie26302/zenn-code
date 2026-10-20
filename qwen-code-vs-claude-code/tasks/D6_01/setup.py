import os, sys
ROWS = {"customers.csv": "id,氏名,住所\n1,髙橋 一郎,東京都港区①丁目\n2,山﨑 花子,大阪府吹田市\n3,渡邉 次郎,福岡県福岡市～中央区\n",
        "orders.csv": "注文番号,商品,数量\nA-001,ノートＰＣ,1\nA-002,ケーブル（Ｃ）,3\n", "memo.csv": "日付,内容\n2025/04/01,№12 の確認\n"}
if __name__ == "__main__":
    d = os.path.join(sys.argv[1], "legacy"); os.makedirs(d)
    for n, t in ROWS.items(): open(os.path.join(d, n), "wb").write(t.encode("cp932"))

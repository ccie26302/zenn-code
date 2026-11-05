# Google Cloud だけが伸びる理由(データと計算)

記事: 「増収額でAWS超え。Google Cloudだけが伸びる理由」(Zenn)

- `data/financials.csv` 各社のクラウド事業の売上・営業利益・受注残・設備投資(2024Q1〜2026Q3、暦年四半期)。出典は SEC に提出された決算書類で、行ごとに URL と注記があります
- `data/market_share.csv` Synergy Research Group の市場規模とシェア
- `data/derived.csv` 増収額、3社の増収額に占める割合、市場の伸びとの差、Synergy から推計したインフラ売上との差
- `data/timeline.csv` 大口契約や TPU 販売の開始などの出来事と、その四半期の数字
- `scripts/` 取得(`fetch_sec.py`)、表の作成、計算(`derive.py`)、グラフ(`charts.py`)
- `run.sh` 一式を再実行します。SEC のアクセスには User-Agent に連絡先が必要なので、`YOUR_NAME your-email@example.com` を自分のものに置き換えてください

注意: Google Cloud には Workspace・TPU の販売・Wiz が含まれ、AWS とは同じ物差しではありません。Azure の金額は一部が成長率からの推計です。Synergy は過去の値を改訂することがあります。詳しくは各 CSV の note 列を見てください。

個人の分析で、所属組織の見解ではありません。

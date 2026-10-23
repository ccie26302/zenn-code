# 脆弱性が毎晩出る時期に、Google Cloud はどこまで守れるか

Zenn の記事「脆弱性が毎晩出る今こそ、Google Cloudに移ろう」の検証の手順とデータです。攻撃の再現はせず、守る側の設定が効くかだけを測っています。

- `PLAN.md` 計画(測定前)
- `e1/` Cloud Run の PHP ランタイム(ベースイメージの自動更新あり)の版を返すアプリと、版を30分ごとに記録するスクリプト。結果は `results/e1_versions.txt`、`results/e1_watch.csv`
- `e2/` 自分で作ったコンテナの入れ替えと戻しの時間(`results/e2_swap.csv`)、イメージの脆弱性スキャンの結果(`results/e2_scan.txt`、`results/e2_scan_watch.csv`)、確かめた Dockerfile
- `e3/` 外への通信を確かめるアプリ(宛先は固定)。結果は `results/e3_egress.csv`
- `e5/` 証明書(eMudhra)・Python(Pillow、certifi)・Go の部品とスキャンを確かめた Dockerfile とプログラム。結果は `results/e5_summary.md`、`results/e5_scan_watch.csv`
- `e6/` 証明書: Cloud Run と API Gateway の URL の証明書(`default_certs.txt`)と、証明書の検証つきの稼働時間のチェックの集計(`uptime_result.sh`、結果は `results/e6_*`)
- `e4/` API Gateway の OpenAPI の定義、認可の確認を切り替えられる小さな API、呼び出し方ごとの確認のスクリプト。結果は `results/e4_auth.csv`

プロジェクト ID などは `<project-id>` に置き換えています。使い捨てのプロジェクトで、`$PROJECT_ID` を自分の値にして流してください。

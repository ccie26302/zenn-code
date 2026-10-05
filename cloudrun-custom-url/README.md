# cloudrun-custom-url

Zenn 記事「Cloud Runの独自URLは消すと取り戻せない」の手順とデータです。Cloud Run の独自URL(`*.cloud.run`、プレビュー)を、同じアカウントの2つのプロジェクト(A・B)で確かめました。

| パス | 中身 |
|---|---|
| measure_release.sh | 自分の2つのプロジェクトで、A が削除した独自URL を B が1回だけ作成できるかを確かめ、削除からの経過秒と応答を記録する |
| data/release_events.csv | 3回分の主な出来事(A の削除、B の作成成功、初めて B のサービスの応答が返った時点)。このデータは旧版のスクリプト(作成の前に応答の確認を挟み、失敗したら作成を再試行する形)で採った。B は3回とも初回の作成で成功したので、今の measure_release.sh と結果は同じ。イベント名だけ claimed_by_B から created_by_B に改名した |
| data/name_rules.txt | 名前の規則の確認(長さ、ハイフン、アンダースコア) |
| data/auth_summary.txt | 認証必須のサービスでの独自URL と run.app の応答 |
| data/evidence.txt | 元の持ち主による再作成のエラー(2リージョン)、既定 URL の無効化、ingress internal、証明書、監査ログのメソッド名 |

他社のブランド名や紛らわしい名前を取る実験はしていません。再現するときも、自分で考えた無害な名前だけを使ってください。

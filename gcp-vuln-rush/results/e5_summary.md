# E5 証明書(eMudhra)・Python・Go の部品と Google Cloud(2026-10-23 JST 午前)

## OS の証明書の一覧(Google の PHP ランタイム、Ubuntu 22.04 ベース)
- php84_20261020_8_4_25_RC01 と php84_20261022_8_4_27_RC01 とも ca-certificates 20260816ubuntu0.22.04.1、ルート 120件
- Mozilla が外した「emSign ECC Root CA - G3」は、どちらにも入っていない(入っているのは emSign の C1・C3・G1)。Ubuntu 22.04 の最新の ca-certificates も同じ版

## アプリが自前で持つ証明書の一覧(Python の certifi)
- certifi 2026.7.22: 「emSign ECC Root CA - G3」を含む
- certifi 2026.10.19: 含まない
- 確かめ方: `python -c "import certifi;print('emSign ECC Root CA - G3' in open(certifi.where()).read())"`

## イメージの脆弱性スキャン(Artifact Analysis、置いてから5分以内)
- e5-py-old(pillow 12.3.0、certifi 2026.7.22): 全107件。Pillow の指摘39件(CVE-2026-96639 を含む、修正版 13)と、certifi の指摘1件(GHSA-6q48-6c7w-9gw2、CRITICAL、修正版 2026.10.19。emSign ECC Root CA - G3 の件。指摘の作成 00:37:11Z)。※最初の記録では「certifi の指摘なし・Pillow 40件」と誤って書いた(見張りの抽出が CVE の番号だけを拾い、GHSA を拾っていなかったため。外部の事実確認で指摘されて訂正)
- e5-py-new(pillow 13.0.0、certifi 2026.10.19): 全67件。Pillow・certifi の指摘はなし
- e5-go-old(Go 1.27.2 でビルド)/ e5-go-new(Go 1.27.3): スキャンは FINISHED_SUCCESS、指摘は0件。Go 1.27.3 の証明書の拒否の追加(GO-2026-6809)はスキャンの対象として出ない
- 見張り: results/e5_scan_watch.csv(20分ごと)

## スキャンにかかった時間(Artifact Analysis のメタデータ、UTC)
- e5-py-old: イメージ作成 00:37:03.0 → スキャン完了(lastScanTime)00:37:11.5(約8秒)
- e5-py-new: 00:37:04.2 → 00:37:15.1(約11秒)
- e5-go-old: 00:38:18.2 → 00:38:24.5(約6秒)
- 解析の対象(analysisCompleted): OS、PYPI、GO、NPM、MAVEN、COMPOSER、RUST、RUBYGEMS、NUGET、SECRET
- php-apt-ubu-old(10-22 07:24:56 作成)に今回の PHP の CVE が出たのは、見張りの記録で 10-22 18:15〜18:54 の間(PHP の修正版公開 10-21 14:00 頃から約28〜29時間)。lastScanTime は 10-23 01:48:59(置いた後も見直されている)

## その他の記録(2026-10-23)
- Debian trixie の php8.4-cli は、10-22 16時台(JST)のビルドで 8.4.27-1~deb13u1 が入った(dpkg -l で確認。会話の中で実行)
- PHP 8.4 のランタイムの切り替わりは、新しいインスタンスの起動時に起きていた(20:36:56Z のログは Starting new instance)。動き続けているインスタンスは、そのままでは切り替わらないおそれがある
- php84_20261021_8_4_25_RC03 が Artifact Registry に公開されたのは 18:59:57Z(03:59:57 JST)。ビルド(イメージの Created)は 13:58Z
- API Gateway の所要時間(operations の時刻): 設定の作成 2分44秒、1回目のゲートウェイの作成は 7分26秒で内部エラー、2回目は 6分35秒

# 現場のセキュリティ対策 第2弾: A2B と PHP の重大な脆弱性に、Google Cloud はどこまで効くか(計画 v1、測定前)

日付: 2026-10-22。締切 2026-10-27(コンテスト security-2026-autumn)。打ち出しはユーザーの選択で「安心を前面に」。止まらない部分は限界の節で短く書く。攻撃手法の解説・攻撃コードは書かない・使わない。

## 背景(一次情報)
- A2B 攻撃: NICT の LETTICE が 2026-10-13 に公表(https://www.nict.go.jp/press/2026/10/13-1.html、https://cynex.nict.go.jp/library/261013-01.html)。公開アプリを解析し、裏側の API を狙う。推奨: 公開 API の洗い出しとログ確認、認可の不備(IDOR/BOLA)・SSRF・RCE・SQLi・設定ミスの点検、不要な API の停止と認証情報の再発行
- PHP: CVE-2026-109618 / 109619(CVSS 9.2、ログインなしで RCE)。修正版 8.5.12 / 8.4.27 / 8.3.36 / 8.2.35 を 2026-10-21 に公開(https://www.php.net/archive/2026.php)。IPA の事前注意喚起(https://www.ipa.go.jp/security/security-alert/2026/pre-alert20261021.html)。多数の組織がサービスを停止

## 実験(各条件 N=3 以上、比較は必ず「既定のまま」と「締めた設定」の両側)
E1 ランタイムの自動更新: Cloud Run のソースデプロイ(--base-image php84 / php85 --automatic-updates)で動く PHP の版を返すサービスを作り、PHP_VERSION が修正版かを確かめる。比較: 自分で古い版に固定したコンテナ(php:8.4.26-apache)。ログの base_image_versions も記録
E2 自分で管理するコンテナの入れ替えの速さ: 脆弱性スキャン(Artifact Registry / On-Demand Scanning)が古い版に CVE-2026-109618/109619 を出すか。修正版のイメージに入れ替えるデプロイの時間、トラフィックを前の版へ戻す時間(各3回)
E3 乗っ取られた後の被害範囲: 同じイメージの中で自分の確認スクリプトを走らせる(攻撃コードは使わない)。条件 A=既定(既定の Compute SA、外への通信は開放)、条件 B=締めた設定(権限ゼロの専用 SA、Direct VPC egress で全通信を VPC に入れ、外へ出られない)。調べること: メタデータサーバーからのトークン取得、そのトークンでできること(バケットの一覧・作成、Secret の読み取り、SA の作成)、外のサイトへの接続、メタデータへのヘッダーなしの要求(SSRF の典型)が拒まれるか。各3回
E4 A2B: Cloud Run を「認証必須」にし、API Gateway で JWT(Google の ID トークン)を検証する。直接の呼び出し・トークンなし・改ざんしたトークン・正しいトークンの応答を各3回。認可の不備(他人の ID を指定)は API Gateway では止まらないことも確かめる(限界)

## 費用
数ドル以内(Cloud Run、API Gateway、スキャン 0.26ドル/イメージ)。使い捨てのプロジェクトで行い、記事の push のあとに削除する

## 記録
run.sh と結果の CSV(results/*.csv)を残す。公開は ~/zenn-code/gcp-a2b-php-guard/

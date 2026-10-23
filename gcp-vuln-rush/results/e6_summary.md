# E6 証明書(2026-10-23)
- Cloud Run(*.a.run.app)と API Gateway(*.gateway.dev)の証明書: Google Trust Services の WE2 → GTS Root R4(→ GlobalSign Root CA)。有効期間 2026-09-28〜2026-12-21(約84日)。e6/default_certs.txt
- Cloud Monitoring の稼働時間のチェック(--validate-ssl=true、1分ごと、6地域)。30分間(05:47:46〜06:17:46Z)の記録(results/e6_uptime_final.txt):
  - 自分の Cloud Run(e1-php84): 合格 379、失敗 0
  - untrusted-root.badssl.com: 合格 0、失敗 665
  - expired.badssl.com: 合格 0、失敗 648
  - www.google.com(最初の正常の対照): 合格 235、失敗 432。地域で分かれた(apac-singapore は全合格、usa-iowa・eur-belgium・sa-brazil は全失敗)。原因は確かめていない(証明書以外の応答の違いとみる)ので、対照から外した
- 作成のつまずき: zsh で `set -- $spec` が空白で分割されず、ホストが空になり「malformed host」

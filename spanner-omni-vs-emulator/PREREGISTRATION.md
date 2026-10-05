# 事前登録 — エミュレータ / Spanner Omni / Cloud Spanner の挙動比較

固定日: 2026-10-05(この文書を git にコミットしてから、Cloud Spanner に対して1件目のテストを流す)。
対象版: Spanner Omni 2026.r4-lts(single-server、colima 4 CPU)/ エミュレータ gcr.io/cloud-spanner-emulator/emulator:latest(イメージ作成 2026-09-15)/ Cloud Spanner 無料試用インスタンス(asia-northeast1、Enterprise edition)。クライアントは Python google-cloud-spanner(版は実行時に記録)。

## 主問い
エミュレータでは通る(または本番と違う結果になる)のに Cloud Spanner では違う結果になるものを、Omni なら手元で Cloud Spanner と同じ結果として再現できるか。

## テストの母集団(恣意的に選ばないための規則)
次の3つの一次情報の箇条書きを1項目ずつテストにする。クライアントから観測できないもの(性能、監視・監査ログ、IAM・TLS の有無)は「観測不能」として一覧に残し、テストしない。

- S1: エミュレータのドキュメント「Limitations and differences」(sources/spanner_docs_emulator.txt)
- S2: エミュレータ README「Notable limitations」(sources/emulator_README.md)
- S3: Omni の「Feature support and compatibility」の非対応機能(sources/spanner-omni_differences.txt)。無料試用インスタンスで使えないものは「対象外」
- C: 対照。エミュレータ README の「Notable supported features」から、本番と同じになるはずの基本機能を選ぶ(ハーネスの誤検知を測る)

## 観測と判定(3層)
各テストは結果を次の形で記録する: `status`(OK か gRPC のステータスコード名)、`value`(意味のある結果を正規化した値。行の集合、件数、計画のノード数の有無など)、`message`(エラー文言の先頭200字)。

- 層1: status が一致するか
- 層2: status と value が一致するか(性質で判定するものは性質が成り立つか)
- 層3: message が一致するか(参考。エラー文言は API 契約ではないとエミュレータ README が明記)
- 正解は Cloud Spanner。各ターゲットで K=5 回流し、同じターゲットの5回で結果が割れたものは「非決定的」として別扱い(A/A の誤検知)。

## 公開の規則(ライセンス 3.4 への配慮)
- 一致率・件数・時間・メモリは公開しない。テストごとに「Cloud / エミュレータ / Omni」の結果を定性的に並べ、再現スクリプトを公開する。
- Omni のライセンスキー、内部のスタックトレースは載せない。

## テスト一覧と事前の予想
予想の記号: 同=Cloud と同じ結果、違=Cloud と違う結果、?=予想なし。予想はドキュメントの記述から立てる(Omni は「同じクエリエンジン」とされるので、S3 以外は「同」と予想)。

| ID | 出典 | 内容 | 観測 | 予想 エミュ | 予想 Omni |
|---|---|---|---|---|---|
| A1 | S1/S2 | 別々の行を更新する読み書きトランザクション2本を同時に実行 | 各トランザクションの関数の呼び出し回数、最終値 | 違(片方が中断) | 同(どちらも1回) |
| A2 | S1/S2 | 同じ行の read-modify-write 2本を同時に実行 | 呼び出し回数、片方が読んだ時点の値、最終値=2 | 違(読む前に中断) | 同 |
| A3 | S1/S2 | 読み書きトランザクション実行中に別テーブルへ DDL | トランザクションと DDL の成否、呼び出し回数 | 違 | 同 |
| A4 | S2 | 重いクエリに 1ms のタイムアウト | status(DEADLINE_EXCEEDED か) | 違(無視して成功) | 同 |
| A5 | S1/S2 | PLAN モードでインデックスを使うクエリ | 計画のノードが返るか、インデックス名が計画に出るか | 違(空) | 同 |
| A6 | S1 | ANALYZE 文 | status | ?(受け付けて無視) | 同 |
| A7 | S1/S2 | Partitioned DML で分割できない文(INSERT) | status | 違(実行される) | 同 |
| A8 | S1/S2 | partitionQuery で root partitionable でないクエリ(ORDER BY) | status | 違(結果が返る) | 同 |
| A9 | S2 | 1コミットのミューテーション上限(80,000)を超える書き込み | status | 違(成功) | 同 |
| A10 | S2 | 1コミットで2種類の制約違反(主キー重複と外部キー違反) | status、どの違反が報告されるか | ? | 同 |
| A11 | S2 | GoogleSQL にあって Spanner にない関数(ST_GEOGPOINT、APPROX_QUANTILES、PARSE_BIGNUMERIC) | status | 違(成功するものがある) | 同 |
| A12 | S2 | SPANNER_SYS のクエリ統計表を読む | status | 違 | 同 |
| A13 | S2 | 書き込み後にサーバ(コンテナ)を再起動して読む | 行が残るか | 違(消える) | 同(残る)。Cloud は再起動できないので「残る」を正解とみなす |
| A14 | S1 | enable_drop_protection を付けた DB を削除 | status | 違(削除できる) | 同 |
| A15 | S2 | 全文検索の language_tag / enhance_query を指定して検索 | status、結果の行 | 違(無視) | enhance_query は違(S3)、language_tag は同 |
| A16 | S2 | リスト API のラベル絞り込み(list_instances の filter=labels) | 結果 | 違 | 同 |
| B1 | S3 | ALTER DATABASE で version_retention_period を 8日・30日に | status | 同(Cloud と同じく拒否?) | 違(30日まで許す) |
| B2 | S3 | CREATE MODEL(REMOTE) | status | ? | 違(非対応) |
| B3 | S3 | partitionQuery に data_boost_enabled=true | status | ? | 違(非対応) |
| C1 | C | テーブルとインデックスの作成、挿入、主キー検索 | 行 | 同 | 同 |
| C2 | C | 外部キー違反 | status | 同 | 同 |
| C3 | C | CHECK 制約違反 | status | 同 | 同 |
| C4 | C | commit timestamp 列(PENDING_COMMIT_TIMESTAMP) | 値が入るか、コミット時刻と一致するか | 同 | 同 |
| C5 | C | 生成列 | 値 | 同 | 同 |
| C6 | C | JSON・NUMERIC 型の往復 | 値 | 同 | 同 |
| C7 | C | exact staleness の読み取り(書き込み前の時刻で読む) | 行の有無 | 同 | 同 |
| C8 | C | INFORMATION_SCHEMA でテーブル一覧 | 行 | 同 | 同 |
| C9 | C | bit-reversed sequence で主キー生成 | 一意か | 同 | 同 |
| C10 | C | Graph(GQL)の簡単な MATCH | 行 | 同 | 同 |
| C11 | C | 主キー重複の INSERT | status | 同 | 同 |
| C12 | C | 存在しないテーブルへのクエリ | status | 同 | 同 |

観測不能として扱うもの: S1 の TLS/認証/IAM、監査ログ・監視、性能。S2 の gRPC と REST の別ポート、Backup API(試用インスタンスで不可)、外部キーの裏の索引名の相互利用。S3 の BigQuery 連携・Knowledge Catalog・地理パーティショニング・tiered storage・増分バックアップ・CMEK・dual-region・大規模 ANN・スケールアップのグラフアルゴリズム(試用インスタンスと1台構成では試せない)。

## 結果を見たあとで変えてよいこと・いけないこと
- テストのコードの誤り(構文、権限)の修正は可。修正は理由と一緒に記録する
- 予想・判定の層・K は変えない
- 新しく見つけた差は「事後の発見」として別の表に分ける

---
## 記録(2026-10-05)
- v1(上記)は、どのターゲットにもテストを流す前に書いた。
- その後、ハーネスの不具合を見つけるため、エミュレータと Omni に各テストを1回ずつ流した(data/pilot/、Cloud には未実行)。この時点で v1 をコミットする。
- 試走で判明したハーネスの欠陥: A4 はクライアント側の期限で3者とも DEADLINE_EXCEEDED になり差を観測できない、A14 は削除保護を DDL で設定しようとして失敗(更新 API で設定するもの)。
- 外部レビュー(分散 DB)で、成立しないテスト・母集団の漏れ・並行性の条件・判定規則の欠如を指摘された。v2 で直す。v2 の変更は「試走でエミュレータと Omni の結果を見たあと」の変更であり、Cloud の結果は見ていない。
- 2026-10-05 ユーザー判断「規約にあるならベンチマークはやめよう」: 性能(遅延・スループット・起動・復旧・メモリ)は測定結果を記録・公開しない。一致率などの集計スコアも公開しない。公開するのはテストごとの挙動の違い(定性)と再現スクリプトのみ。ハーネスの wall_s(所要時間)は記録から外す。

---
# v2(2026-10-05。v1 の外部レビューを反映。エミュレータと Omni の試走を見たあと、Cloud は未実行)

コード: harness/cases_v2.py、run_v2.py、orchestrate.py、restart_test.py(このコミットに含める)。版: google-cloud-spanner 3.71.0、Omni イメージ digest sha256:9dcfd3d25f25…(2026.r4-lts)、エミュレータは実行時に digest を記録。

## 主張の範囲
single-server・arm64(colima、4 CPU)の Omni について、クライアントから見た API と意味論の一致だけを扱う。分散構成・TrueTime・性能は主張しない。性能は測らず、所要時間も記録しない(ライセンス 3.4、ユーザー判断)。

## 主問いの判定規則(結果を見る前に固定)
- 判定の基準: A 群は Cloud の結果、B 群は Omni の差分ページ(S3)の記述、A13 は仕様(永続化されること)
- 「エミュレータ≠Cloud」だったテストそれぞれについて、Omni が Cloud と同じなら「Omni で手元で捕まえられる」、違えば「捕まえられない」と書く
- C 群で Omni≠Cloud があれば、その時点で「Omni は置き換えにならない部分がある」と書く
- 記事では、テストごとに上の判定を定性的に並べる(件数や率は出さない)

## 陽性対照
A5(PLAN)と A14(削除保護)でエミュレータ≠Cloud にならなければ、ハーネスの欠陥とみなして結論を出さない。

## 並行性(A1〜A3)
- 隔離レベル SERIALIZABLE、読み取りロック PESSIMISTIC を明示。Barrier(5秒)で両方が読み終えたことを確かめ、重なりの有無を記録
- K=30(5ラウンド×6)。性質: A1 両方コミット・最終値(1,1)(2,1)、A2 最終値=2。観測: 中断の位置(読む前/読んだ後/コミット時)、重なりの有無、A3 は DDL とトランザクションの成否
- Cloud 自身が性質を破った場合は「基準が不安定」として報告。結果が割れたら除外せず分布を報告(分布は記事では「割れた」とだけ書く)

## テストの変更(v1 から)
- A4(gRPC の期限): クライアント側の期限で3者とも DEADLINE_EXCEEDED になり、サーバが期限を無視するかをクライアントから区別できない。観測不能に移す
- A5: FORCE_INDEX を付け、計画のノードの有無だけを見る。A5b(PROFILE)を追加
- A6: ANALYZE の前後で INFORMATION_SCHEMA.SPANNER_STATISTICS の件数が増えるか
- A7: INSERT に加え、分割できない文として「NOT IN (サブクエリ)の DELETE」「同じテーブルを読む UPDATE」
- A8: 非キー列の ORDER BY と COUNT(*)
- A9: ミューテーション数の境界(8列×10,000行=80,000 と、+1)、1セルのサイズの境界(10MiB と +1 バイト)
- A10: ミューテーションの順序を2通り
- A11: 手選びをやめ、ZetaSQL の関数見出しと Spanner の関数一覧ページの差集合(sources/fn_diff.txt、249件)から、シード 20261005 で20件(sources/fn_sample20.txt)。呼び出しは各関数の最小の文
- A13: graceful(docker stop)と kill -9(docker kill)を各5回、エミュレータと Omni。基準は仕様
- A14: 削除保護を更新 API で設定。設定の成否、長時間オペレーションの完了確認、削除の成否、削除後の存在を分けて記録
- A15: エミュレータ README の全文検索の小項目を DEBUG_TOKENLIST で直接比べる(language_tag、content_type、token_category、TOKENIZE_SUBSTRING の remove_diacritics と short_tokens_only_for_anchors、TOKENIZE_NGRAMS の remove_diacritics、SCORE の options、CREATE SEARCH INDEX の OPTIONS)。enhance_query は Cloud で ON と OFF の結果が違わなければ無効
- A16: ListSessions のラベル絞り込み(通常のセッションを API で作る)
- A17(新規): 外部キーの裏の索引名を INFORMATION_SCHEMA から取り、FORCE_INDEX に使う
- B1: 7d / 8d / 30d / 31d。B2・B3 は Cloud で成功しなければ無効
- C: エミュレータ README の supported 欄の全項目を対象(C13 DDL 変更、C14 DML 件数、C15 SQL なしの読み取り、C16 二次索引の読み取り、C17 Partitioned Read、C18 分割できる Partitioned DML、C19 GENERATE_UUID、C20 PostgreSQL 方言)。除外: Dataflow テンプレートと PGAdapter(別製品が要る)、DML sequence numbers(DML の実行に含まれる)、Admin の長時間オペレーション(DDL に含まれる)
- 対象外: Graph のアルゴリズム(Cloud Storage への EXPORT DATA が必須でプレビュー)、Backup API(試用インスタンスで不可)
- 行は必ずソートして比べる(エミュレータ README の FAQ: 行順はランダム化される)

## 実行
- orchestrate.py で5ラウンド。各ラウンドで3ターゲットの順序を固定シード 20261005 で並べ替える。同じ日に流す
- テストのコードの修正は「3ターゲットすべてで同じように失敗した場合」だけ認め、修正したら全ターゲットで流し直し、元の結果も残す

## 試走で見つけた事後の発見(Cloud 未実行の段階)
- Omni の UpdateDatabase(削除保護の設定)は反映されるが、返る長時間オペレーションを取得すると NOT_FOUND
- Omni は通常のセッションを作れない(多重化セッションのみ)。そのためセッションのラベルも使えない
- Python クライアントは、Omni に対しても既定で多重化セッションを使う

## データベースの割り当て(試用インスタンスは5つまで)
cmp2(本体)、cmppg(PostgreSQL)、dropprot(A14)、予備2つ

---
# v2.1(2026-10-05。v2 の外部レビューを反映。エミュレータと Omni の試走のみ、Cloud 未実行)

## 判定の細則
- 判定は副テスト単位。比べる欄は status と value(副テストは [status, value, message] の status と value)。message・attempts・set_lro・seq は比較対象外(拒否の理由の分類と記録にだけ使う)
- K 回の集約: すべて同じならその値、割れたら「非決定的」。非決定的なものは除外せず、記事では「割れた」と書く
- 並行性(K=30): 「性質(final_ok)がすべて成立するか」「overlap の値の集合」「aborted_at の値の集合」が Cloud と一致すれば同。回数・attempts は比べない。aborted_at のラベルは「クライアントが中断を観測した RPC」(at_read_rpc / after_read / at_commit_rpc)で、原因の発生位置ではない
- 拒否の理由の分類(message に対する正規表現、上から順に最初に当たったもの): FN_NOT_FOUND `Function not found|Unrecognized name` / UNSUPPORTED `[Uu]nsupported|not supported|UNIMPLEMENTED|Unimplemented` / SIGNATURE `No matching signature` / PARTITION `partition` / LIMIT `too many|exceed|too large|maximum|limit` / CONCURRENT `concurrent` / OTHER
- A11 の判定は「受理か拒否か」だけ(拒否のステータスコードは製品ごとに違うため比べない)。Cloud が受理した関数は差集合の抽出の誤りとして除外し、その旨を書く
- 文書に書かれたエミュレータの制限が再現しなかったもの(エミュレータ=Cloud だった A テスト)は「文書の記述が現行版では再現しなかった」として別に報告する
- A9: Cloud が 80,001 件を受理したら、ミューテーション数の境界の副テストは無効(数え方の前提が違う)。160,000 件は遠く超える対照
- A15: エミュレータは DEBUG_TOKENLIST が無い(試走で Function not found)。その場合 remove_diacritics は search_remove_diacritics(SEARCH_SUBSTRING で 'cafe' が 'café' に当たるか)で判定する。enhance_query は Cloud で5ラウンドすべて on≠off のときだけ有効。Omni の結果は「エラー」と「黙殺(on=off)」に分ける
- A14 の陽性対照は「削除の成否」の差で判定する。エミュレータは削除保護の設定 API 自体が UNIMPLEMENTED で、S1 の「保護を無視する」とは理由が違うことを併記する

## Cloud 側の無効・非実行(結果を見る前に確定)
- B2: endpoint は実在しない(Vertex AI はこのプロジェクトで有効にしない)。Cloud 側の結果は無効とし、Omni は S3 の記述との照合だけ
- B3: Data Boost は課金の可能性があるので Cloud では流さない(SKIPPED_BY_PREREG)。Omni は S3 の記述との照合だけ
- 一時的なエラー(UNAVAILABLE / RESOURCE_EXHAUSTED / UNAUTHENTICATED)はその回を無効とし、1回だけ流し直す
- B1 は予備の DB(cmpb1)で流す

## ハーネスの変更
- sub が message を返す、A3 は最初の読み取りを Event で待ってから DDL(順序を seq に記録)、A14 の各段階を囲む、DDL の名前と生データに run_id、生データにイメージの digest、orchestrate の最後に完全性の検査、A13 は graceful と kill9 で行を分け docker stop -t 120
- A13 の範囲: kill -9 は colima の VM のページキャッシュを越えないので、電源断での永続性(fsync)は検証しない

## 第三者による時刻の検証
公開リモートは未設定のため、事前登録の時刻はこのローカル git のコミットでしか示せない(限界として記事に書く)。

---
## 追記(公開時、2026-10-05。上の本文は書き換えていない)
- 本文中の「ユーザー判断」は、筆者の判断の意味。
- 本番(run_id=main1)のあと、独立監査で A9 のセル上限のテストの誤り(Python クライアントは bytes を base64 済みとして送る)が見つかり、修正して3ターゲットで流し直した(run_id=fix_a9)。fix_a9 の行は orchestrate を通していないため omni_digest・emu_digest が空だが、同じ日に同じイメージ(main1 の行に記録した digest)のまま実行した。
- 最終の判定(analyze_final.py)には、結果を見たあとの変更が入っている(比べる欄の選び直し、A3 の txn_retried の除外、A11 の除外、A15 の判定不能の明記)。事前登録どおりの集計は analyze.py / ANALYSIS.md。
- 事後の検証(posthoc/)は事前登録の外。

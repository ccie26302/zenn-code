# 最終の判定(独立監査の反映後。件数・率は記事に出さない)

| テスト | 判定 | 副テストごと(Cloud と比べて) | 注記 |
|---|---|---|---|
| A1 | Omni で捕まえられる | overlap: エミュ≠ Omni=; aborted_at: エミュ≠ Omni= | 比べたのは重なりの有無と中断を観測した RPC の集合。エミュレータの分布は Barrier の待ち時間に左右される |
| A2 | Omni で捕まえられる | overlap: エミュ≠ Omni=; aborted_at: エミュ≠ Omni= |  |
| A3 | Omni で捕まえられる | ddl: エミュ≠ Omni= | txn_retried は事前登録で比較対象外。本番は再試行なし、Omni とエミュレータ(DDL が通った回)は DDL と重なったトランザクションが再試行された(事後の対照で DDL なしでは Omni・本番とも再試行なし) |
| A5 | Omni で捕まえられる | -: エミュ≠ Omni= | 計画が返るかだけを比べた(中身は比べていない) |
| A5b | Omni で捕まえられる | -: エミュ≠ Omni= |  |
| A6 | Omni で捕まえられる | -: エミュ≠ Omni= | 統計パッケージが増えるかだけを比べた(統計の中身は比べていない) |
| A7 | エミュレータも本番と同じ(文書の制限は、試した入力では再現せず) | delete_not_in_subquery: エミュ= Omni=; update_self_read: エミュ= Omni=; insert: エミュ= Omni= |  |
| A8 | エミュレータも本番と同じ(文書の制限は、試した入力では再現せず) | order_by_nonkey: エミュ= Omni=; count_star: エミュ= Omni= |  |
| A9 | Omni でも捕まえられない | mut_80001: エミュ≠ Omni≠; mut_160000: エミュ≠ Omni=; cell_10MiB: エミュ≠ Omni=; cell_10MiB_plus1: エミュ≠ Omni= | base64 の扱いを直した再実行。事後の二分探索: Cloud・Omni とも1セルの最大は 10MiB−4 バイト、ミューテーションの上限は Cloud 80,000・Omni 120,000(行×列で数える点は同じ) |
| A10 | Omni で捕まえられる | dup_first: エミュ≠ Omni=; fk_first: エミュ≠ Omni= |  |
| A12 | Omni で捕まえられる | -: エミュ≠ Omni= |  |
| A14 | Omni で捕まえられる | drop: エミュ≠ Omni=; exists_after_drop: エミュ≠ Omni= | Omni は削除保護の更新の長時間オペレーションが NOT_FOUND を返す(op.result() を待つコードは Omni でだけ失敗する) |
| A16 | Omni でも捕まえられない | -: エミュ≠ Omni≠ | 向きが逆: 本番で通る ListSessions のラベル付きセッションが、Omni では作れない(多重化セッションのみ)。ListInstances の絞り込みは未検証 |
| A17 | Omni で捕まえられる | -: エミュ≠ Omni= |  |
| A11 | エミュレータも本番と同じ(文書の制限は、試した入力では再現せず) | 除外(Cloud が受理=APPROX_COUNT_DISTINCT)以外の関数はすべて3者とも拒否 | 除外した関数をエミュレータは拒否した(事後の発見: エミュレータが本番にある関数を拒否する) |
| A15 search_remove_diacritics.rd_index | Omni で捕まえられる | Cloud=('OK', '[1]') エミュ=('OK', '[]') Omni=('OK', '[1]') | |
| A15 content_type_html | エミュレータは判定不能(DEBUG_TOKENLIST が無い)。Omni は 本番と同じ | Cloud=('OK', 'OK', True) エミュ=('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) Omni=('OK', 'OK', True) | |
| A15 token_category_title | エミュレータは判定不能(DEBUG_TOKENLIST が無い)。Omni は 本番と同じ | Cloud=('OK', 'OK', True) エミュ=('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) Omni=('OK', 'OK', True) | |
| A15 substring_short_tokens_only_for_anchors | エミュレータは判定不能(DEBUG_TOKENLIST が無い)。Omni は 本番と同じ | Cloud=('OK', 'OK', True) エミュ=('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) Omni=('OK', 'OK', True) | |
| A15 substring_remove_diacritics | エミュレータは判定不能(DEBUG_TOKENLIST が無い)。Omni は 本番と同じ | Cloud=('OK', 'OK', True) エミュ=('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) Omni=('OK', 'OK', True) | |
| A15 ngrams_remove_diacritics | エミュレータは判定不能(DEBUG_TOKENLIST が無い)。Omni は 本番と同じ | Cloud=('OK', 'OK', True) エミュ=('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) Omni=('OK', 'OK', True) | |
| A15 language_tag_ja | 判定不能(Cloud でも引数の効果が出ない、または status しか見ていない) | Cloud=('OK', 'OK', False) エミュ=('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) Omni=('OK', 'OK', False) | |
| A15 search_index_options | 判定不能(Cloud でも引数の効果が出ない、または status しか見ていない) | Cloud=('OK', 'null') エミュ=('OK', 'null') Omni=('OK', 'null') | |
| A15 score_options | Omni で捕まえられる | Cloud=('OK', 'true') エミュ=('OK', 'false') Omni=('OK', 'true') | |
| A15 enhance_query | Cloud は on≠off(有効)。エミュレータと Omni は on=off で、エラーにならず黙って無視(Omni は差分ページで非対応と明記) | on=(('OK', '[1, 3]'), ('OK', '[3]'), ('OK', '[3]')) off=(('OK', '[3]'), ('OK', '[3]'), ('OK', '[3]')) | |
| B1 | Omni は 8d・30d を受理、31d を拒否 = S3「30日まで」と一致。Cloud とエミュレータは 7d まで | Omni=('OK', '{"30d": "OK", "31d": "INVALID_ARGUMENT", "7d": "OK", "8d": "OK"}') | 保持期間はエミュレータのほうが本番に近い |
| B2 | Omni は UNIMPLEMENTED = S3「MODEL は非対応」と一致(Cloud 側は事前登録どおり無効) | Omni=('UNIMPLEMENTED', 'null') | |
| B3 | Omni は Data Boost を拒否 = S3 と一致(Cloud は事前登録どおり実行せず) | Omni=('INVALID_ARGUMENT', 'null') | |

- 対照(C 群): 3者すべて一致 = True
- 陽性対照: A5 エミュ≠Cloud = True、A14 エミュ≠Cloud = True
- A13(再起動、基準は仕様): エミュレータは停止のたびに DB ごと消え、Omni は graceful・kill -9 とも行が残った(コンテナの停止までで、電源断の永続性は検証していない)

# 集計(run_id=main1、事前登録 v2.1 の規則)

| テスト | 副テスト | Cloud | エミュレータ | Omni | エミュ=Cloud | Omni=Cloud | 判定 | 拒否の理由(エミュ/Omni/Cloud) |
|---|---|---|---|---|---|---|---|---|
| A1 | aborted_at | ('()',) | ("('at_commit_rpc', 'at_read_rpc')", "('at_commit_rpc',)", " | ('()',) | × | ○ | Omni で捕まえられる | -/-/- |
| A1 | final_ok | True | True | True | ○ | ○ | 文書の記述が現行版で再現せず | -/-/- |
| A1 | overlap | ('True',) | ('False', 'True') | ('True',) | × | ○ | Omni で捕まえられる | -/-/- |
| A2 | aborted_at | ("('at_commit_rpc',)",) | ("('at_commit_rpc', 'at_read_rpc')", "('at_commit_rpc',)", " | ("('at_commit_rpc',)",) | × | ○ | Omni で捕まえられる | -/-/- |
| A2 | final_ok | True | True | True | ○ | ○ | 文書の記述が現行版で再現せず | -/-/- |
| A2 | overlap | ('True',) | ('False', 'True') | ('True',) | × | ○ | Omni で捕まえられる | -/-/- |
| A3 | ddl | ('OK',) | ('FAILED_PRECONDITION', 'OK') | ('OK',) | × | ○ | Omni で捕まえられる | -/-/- |
| A3 | txn | ('OK',) | ('OK',) | ('OK',) | ○ | ○ | 文書の記述が現行版で再現せず | -/-/- |
| A3 | txn_retried | ('False',) | ('False', 'True') | ('False', 'True') | × | × | Omni でも捕まえられない | -/-/- |
| A5 | - | ('OK', '{"has_plan_nodes": true}') | ('OK', '{"has_plan_nodes": false}') | ('OK', '{"has_plan_nodes": true}') | × | ○ | Omni で捕まえられる | -/-/- |
| A5b | - | ('OK', '{"has_plan_nodes": true, "rows": 30, "rows_returned_ | ('OK', '{"has_plan_nodes": false, "rows": 30, "rows_returned | ('OK', '{"has_plan_nodes": true, "rows": 30, "rows_returned_ | × | ○ | Omni で捕まえられる | -/-/- |
| A6 | - | ('OK', '{"analyze": "OK", "package_increased": true, "stats_ | ('OK', '{"analyze": "OK", "package_increased": false, "stats | ('OK', '{"analyze": "OK", "package_increased": true, "stats_ | × | ○ | Omni で捕まえられる | -/-/- |
| A7 | delete_not_in_subquery | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ○ | ○ | 文書の記述が現行版で再現せず | PARTITION/PARTITION/PARTITION |
| A7 | insert | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ○ | ○ | 文書の記述が現行版で再現せず | UNSUPPORTED/UNSUPPORTED/UNSUPPORTED |
| A7 | update_self_read | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ○ | ○ | 文書の記述が現行版で再現せず | PARTITION/PARTITION/PARTITION |
| A8 | count_star | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ○ | ○ | 文書の記述が現行版で再現せず | PARTITION/PARTITION/PARTITION |
| A8 | order_by_nonkey | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ○ | ○ | 文書の記述が現行版で再現せず | PARTITION/PARTITION/PARTITION |
| A9 | cell_10MiB | ('OK', 'null') | ('OK', 'null') | ('OK', 'null') | ○ | ○ | 文書の記述が現行版で再現せず | -/-/- |
| A9 | cell_10MiB_plus1 | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ○ | ○ | 文書の記述が現行版で再現せず | OTHER/OTHER/OTHER |
| A9 | mut_160000 | ('INVALID_ARGUMENT', 'null') | ('OK', 'null') | ('INVALID_ARGUMENT', 'null') | × | ○ | Omni で捕まえられる | -/LIMIT/LIMIT |
| A9 | mut_80000 | ('OK', 'null') | ('OK', 'null') | ('OK', 'null') | ○ | ○ | 文書の記述が現行版で再現せず | -/-/- |
| A9 | mut_80001 | ('INVALID_ARGUMENT', 'null') | ('OK', 'null') | ('OK', 'null') | × | × | Omni でも捕まえられない | -/-/LIMIT |
| A10 | dup_first | ('FAILED_PRECONDITION', '"foreign_key"') | ('ALREADY_EXISTS', '"already_exists"') | ('FAILED_PRECONDITION', '"foreign_key"') | × | ○ | Omni で捕まえられる | OTHER/OTHER/OTHER |
| A10 | fk_first | ('FAILED_PRECONDITION', '"foreign_key"') | ('ALREADY_EXISTS', '"already_exists"') | ('FAILED_PRECONDITION', '"foreign_key"') | × | ○ | Omni で捕まえられる | OTHER/OTHER/OTHER |
| A11 | APPROX_COUNT_DISTINCT | accept | reject | accept | × | ○ | Omni で捕まえられる | UNSUPPORTED/-/- |
| A11 | COTH | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | UNSUPPORTED/UNSUPPORTED/UNSUPPORTED |
| A11 | COVAR_POP | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | UNSUPPORTED/UNSUPPORTED/UNSUPPORTED |
| A11 | CUME_DIST | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | UNSUPPORTED/UNSUPPORTED/UNSUPPORTED |
| A11 | DETERMINISTIC_DECRYPT_BYTES | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/FN_NOT_FOUND/FN_NOT_FOUND |
| A11 | IS_LAST | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | UNSUPPORTED/UNSUPPORTED/UNSUPPORTED |
| A11 | JSON_EXTRACT_ARRAY | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | UNSUPPORTED/UNSUPPORTED/UNSUPPORTED |
| A11 | JSON_EXTRACT_SCALAR | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | UNSUPPORTED/UNSUPPORTED/UNSUPPORTED |
| A11 | JSON_FLATTEN | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/FN_NOT_FOUND/FN_NOT_FOUND |
| A11 | MAP_CARDINALITY | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/UNSUPPORTED/UNSUPPORTED |
| A11 | MAP_EMPTY | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/UNSUPPORTED/UNSUPPORTED |
| A11 | MAP_KEYS_SORTED | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/UNSUPPORTED/UNSUPPORTED |
| A11 | PERCENTILE_CONT | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | UNSUPPORTED/UNSUPPORTED/UNSUPPORTED |
| A11 | PI_BIGNUMERIC | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/FN_NOT_FOUND/FN_NOT_FOUND |
| A11 | PROTO_DEFAULT_IF_NULL | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/FN_NOT_FOUND/FN_NOT_FOUND |
| A11 | PROTO_MODIFY_MAP | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/FN_NOT_FOUND/FN_NOT_FOUND |
| A11 | ST_ASBINARY | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/FN_NOT_FOUND/FN_NOT_FOUND |
| A11 | ST_DISTANCE | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/FN_NOT_FOUND/FN_NOT_FOUND |
| A11 | ST_EQUALS | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/FN_NOT_FOUND/FN_NOT_FOUND |
| A11 | ST_TOUCHES | reject | reject | reject | ○ | ○ | 文書の記述が現行版で再現せず | FN_NOT_FOUND/FN_NOT_FOUND/FN_NOT_FOUND |
| A12 | - | ('OK', 'true') | ('INVALID_ARGUMENT', 'null') | ('OK', 'true') | × | ○ | Omni で捕まえられる | OTHER/-/- |
| A14 | drop | FAILED_PRECONDITION | OK | FAILED_PRECONDITION | × | ○ | Omni で捕まえられる | -/-/- |
| A14 | exists_after_drop | True | False | True | × | ○ | Omni で捕まえられる | -/-/- |
| A14 | set_protection | OK | UNIMPLEMENTED | OK | × | ○ | Omni で捕まえられる | -/-/- |
| A15 | content_type_html | ('OK', 'OK', True) | ('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) | ('OK', 'OK', True) | × | ○ | Omni で捕まえられる | FN_NOT_FOUND/-/- |
| A15 | enhance_query_off | ('OK', '[3]') | ('OK', '[3]') | ('OK', '[3]') | ○ | ○ | 文書の記述が現行版で再現せず | -/-/- |
| A15 | enhance_query_on | ('OK', '[1, 3]') | ('OK', '[3]') | ('OK', '[3]') | × | × | Omni でも捕まえられない | -/-/- |
| A15 | language_tag_ja | ('OK', 'OK', False) | ('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) | ('OK', 'OK', False) | × | ○ | Omni で捕まえられる | FN_NOT_FOUND/-/- |
| A15 | ngrams_remove_diacritics | ('OK', 'OK', True) | ('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) | ('OK', 'OK', True) | × | ○ | Omni で捕まえられる | FN_NOT_FOUND/-/- |
| A15 | score_options | ('OK', 'true') | ('OK', 'false') | ('OK', 'true') | × | ○ | Omni で捕まえられる | -/-/- |
| A15 | search_index_options | ('OK', 'null') | ('OK', 'null') | ('OK', 'null') | ○ | ○ | 文書の記述が現行版で再現せず | -/-/- |
| A15 | search_remove_diacritics.plain_index | ('OK', '[]') | ('OK', '[]') | ('OK', '[]') | ○ | ○ | 文書の記述が現行版で再現せず | -/-/- |
| A15 | search_remove_diacritics.rd_index | ('OK', '[1]') | ('OK', '[]') | ('OK', '[1]') | × | ○ | Omni で捕まえられる | -/-/- |
| A15 | substring_remove_diacritics | ('OK', 'OK', True) | ('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) | ('OK', 'OK', True) | × | ○ | Omni で捕まえられる | FN_NOT_FOUND/-/- |
| A15 | substring_short_tokens_only_for_anchors | ('OK', 'OK', True) | ('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) | ('OK', 'OK', True) | × | ○ | Omni で捕まえられる | FN_NOT_FOUND/-/- |
| A15 | token_category_title | ('OK', 'OK', True) | ('INVALID_ARGUMENT', 'INVALID_ARGUMENT', None) | ('OK', 'OK', True) | × | ○ | Omni で捕まえられる | FN_NOT_FOUND/-/- |
| A16 | - | ('OK', '{"match_contains": true, "nomatch_contains": false}' | ('OK', '{"match_contains": true, "nomatch_contains": true}') | ('INVALID_ARGUMENT', 'null') | × | × | Omni でも捕まえられない | -/OTHER/- |
| A17 | - | ('OK', '{"backing_index_found": true, "force_index": "OK"}') | ('OK', '{"backing_index_found": true, "force_index": "INVALI | ('OK', '{"backing_index_found": true, "force_index": "OK"}') | × | ○ | Omni で捕まえられる | -/-/- |
| B1 | - | ('OK', '{"30d": "INVALID_ARGUMENT", "31d": "INVALID_ARGUMENT | ('OK', '{"30d": "INVALID_ARGUMENT", "31d": "INVALID_ARGUMENT | ('OK', '{"30d": "OK", "31d": "INVALID_ARGUMENT", "7d": "OK", | ○ | × | S3 と照合 | -/-/- |
| B2 | - | ('非決定的', ("('NOT_FOUND', 'null')", "('PERMISSION_DENIED', 'n | ('OK', 'null') | ('UNIMPLEMENTED', 'null') | × | × | S3 と照合 | -/UNSUPPORTED/OTHER |
| B3 | - | ('SKIPPED_BY_PREREG', 'null') | ('OK', '[0, 1, 2]') | ('INVALID_ARGUMENT', 'null') | × | × | S3 と照合 | -/OTHER/- |
| C1 | - | ('OK', '[[3, "c3", 111], [150, "c0", 150]]') | ('OK', '[[3, "c3", 111], [150, "c0", 150]]') | ('OK', '[[3, "c3", 111], [150, "c0", 150]]') | ○ | ○ | 対照: 一致 | -/-/- |
| C2 | - | ('FAILED_PRECONDITION', 'null') | ('FAILED_PRECONDITION', 'null') | ('FAILED_PRECONDITION', 'null') | ○ | ○ | 対照: 一致 | OTHER/OTHER/OTHER |
| C3 | - | ('OUT_OF_RANGE', 'null') | ('OUT_OF_RANGE', 'null') | ('OUT_OF_RANGE', 'null') | ○ | ○ | 対照: 一致 | OTHER/OTHER/OTHER |
| C4 | - | ('OK', '{"has_value": true}') | ('OK', '{"has_value": true}') | ('OK', '{"has_value": true}') | ○ | ○ | 対照: 一致 | -/-/- |
| C5 | - | ('OK', '42') | ('OK', '42') | ('OK', '42') | ○ | ○ | 対照: 一致 | -/-/- |
| C6 | - | ('OK', '{"j": {"a": [1, 2], "b": "x"}, "n": "12345.6789"}') | ('OK', '{"j": {"a": [1, 2], "b": "x"}, "n": "12345.6789"}') | ('OK', '{"j": {"a": [1, 2], "b": "x"}, "n": "12345.6789"}') | ○ | ○ | 対照: 一致 | -/-/- |
| C7 | - | ('OK', '{"at": 1, "before": 0}') | ('OK', '{"at": 1, "before": 0}') | ('OK', '{"at": 1, "before": 0}') | ○ | ○ | 対照: 一致 | -/-/- |
| C8 | - | ('OK', '["Acc", "Big8", "Blob", "Child", "Chk", "Dia", "Doc" | ('OK', '["Acc", "Big8", "Blob", "Child", "Chk", "Dia", "Doc" | ('OK', '["Acc", "Big8", "Blob", "Child", "Chk", "Dia", "Doc" | ○ | ○ | 対照: 一致 | -/-/- |
| C9 | - | ('OK', '{"n": 5, "positive": true, "unique": true}') | ('OK', '{"n": 5, "positive": true, "unique": true}') | ('OK', '{"n": 5, "positive": true, "unique": true}') | ○ | ○ | 対照: 一致 | -/-/- |
| C10 | - | ('OK', '[["alice", "bob"], ["bob", "carol"]]') | ('OK', '[["alice", "bob"], ["bob", "carol"]]') | ('OK', '[["alice", "bob"], ["bob", "carol"]]') | ○ | ○ | 対照: 一致 | -/-/- |
| C11 | - | ('ALREADY_EXISTS', 'null') | ('ALREADY_EXISTS', 'null') | ('ALREADY_EXISTS', 'null') | ○ | ○ | 対照: 一致 | OTHER/OTHER/OTHER |
| C12 | - | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ('INVALID_ARGUMENT', 'null') | ○ | ○ | 対照: 一致 | OTHER/OTHER/OTHER |
| C13 | - | ('OK', 'null') | ('OK', 'null') | ('OK', 'null') | ○ | ○ | 対照: 一致 | -/-/- |
| C14 | - | ('OK', '30') | ('OK', '30') | ('OK', '30') | ○ | ○ | 対照: 一致 | -/-/- |
| C15 | - | ('OK', '[10, 11, 12, 13, 14]') | ('OK', '[10, 11, 12, 13, 14]') | ('OK', '[10, 11, 12, 13, 14]') | ○ | ○ | 対照: 一致 | -/-/- |
| C16 | - | ('OK', '[3, 13, 23, 33, 43, 53, 63, 73, 83, 93, 103, 113, 12 | ('OK', '[3, 13, 23, 33, 43, 53, 63, 73, 83, 93, 103, 113, 12 | ('OK', '[3, 13, 23, 33, 43, 53, 63, 73, 83, 93, 103, 113, 12 | ○ | ○ | 対照: 一致 | -/-/- |
| C17 | - | ('OK', '300') | ('OK', '300') | ('OK', '300') | ○ | ○ | 対照: 一致 | -/-/- |
| C18 | - | ('OK', 'true') | ('OK', 'true') | ('OK', 'true') | ○ | ○ | 対照: 一致 | -/-/- |
| C19 | - | ('OK', '{"len36": true, "n": 3, "unique": true}') | ('OK', '{"len36": true, "n": 3, "unique": true}') | ('OK', '{"len36": true, "n": 3, "unique": true}') | ○ | ○ | 対照: 一致 | -/-/- |
| C20 | - | ('OK', '[[1, "a"], [2, "b"]]') | ('OK', '[[1, "a"], [2, "b"]]') | ('OK', '[[1, "a"], [2, "b"]]') | ○ | ○ | 対照: 一致 | -/-/- |

## A13(再起動。基準は仕様=永続化)

- emu graceful: {'{"db_exists": false, "row": false}': 5}
- emu kill9: {'{"db_exists": false, "row": false}': 5}
- omni graceful: {'{"db_exists": true, "row": true}': 5}
- omni kill9: {'{"db_exists": true, "row": true}': 5}

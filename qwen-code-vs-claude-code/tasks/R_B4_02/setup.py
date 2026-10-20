import os, sys
sys.path.insert(0, "/tasks")
from jlib import write
SPEC = '''# todo.py の仕様

コマンドラインの ToDo 管理ツール。データは環境変数 TODO_FILE のパス(なければ ./todo.json)に JSON で保存する。

## データ

- JSON の配列。要素は {"id": 整数, "title": 文字列, "done": 真偽値, "due": "YYYY-MM-DD" または null}
- id は 1 から始まり、追加のたびに「今ある最大の id + 1」(空なら 1)

## コマンド

| コマンド | 動き | 標準出力 | 終了コード |
|---|---|---|---|
| `add TITLE [--due YYYY-MM-DD]` | 追加する | `added <id>` | 0 |
| `list` | 未完了だけを id 順に出す | 1件ごとに `<id> [ ] <title>`。期限があれば末尾に ` (due <YYYY-MM-DD>)` | 0 |
| `list --all` | 完了も含めて id 順 | 完了は `[x]` | 0 |
| `done ID` | 完了にする | `done <id>` | 0 |
| `remove ID` | 消す | `removed <id>` | 0 |

## エラー

- 存在しない ID: 標準エラーに `error: no such id <id>`、終了コード 2
- `--due` の日付が YYYY-MM-DD の実在する日付でない: 標準エラーに `error: invalid date <値>`、終了コード 2(データは変えない)
- TITLE が空文字や空白だけ: 標準エラーに `error: empty title`、終了コード 2
- 未完了が0件のときの `list` は何も出さず、終了コード 0
- 保存ファイルが壊れている(JSON として読めない): 標準エラーに `error: broken data file`、終了コード 3。ファイルは上書きしない
'''
if __name__ == "__main__": write(sys.argv[1], {"SPEC.md": SPEC, "tests/.keep": ""})

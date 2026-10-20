#!/bin/bash
# Claude Code のトークンを発行して保存する(トークンは画面に出さずにファイルへ書く)
D=$HOME/googleCloud/qwencode/harness/secrets/claude; mkdir -p "$D"; chmod 700 "$D"
echo "=== 手順1: 下に出る URL をブラウザで開いてログインし、最後に表示されるトークン(sk-ant- で始まる文字列)をコピーしてください ==="
docker run --rm -it qwen-agent claude setup-token
echo
read -r -s -p "=== 手順2: コピーしたトークンをここに貼り付けて Enter を押してください(画面には表示されません): " TOK; echo
TOK=$(printf '%s' "$TOK" | tr -d '[:space:]')
case "$TOK" in
  sk-ant-*) printf '%s' "$TOK" > "$D/token"; chmod 600 "$D/token"; echo "=== 保存しました。この画面は閉じてかまいません ===" ;;
  *) echo "=== トークンの形ではありませんでした。もう一度このコマンドを流してください ===" ;;
esac

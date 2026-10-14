#!/bin/bash
# 惜しい誤答: 隠しファイルをまとめて除外する(.gitignore なども落ちる)
cd "$1"
tar --exclude='.*' --exclude='*.pem' -czpf backup.tar.gz app

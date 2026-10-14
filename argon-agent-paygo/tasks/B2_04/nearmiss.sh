#!/bin/bash
# 惜しい誤答: コンフリクトを main 側(ours)で片付ける。retry の実装が消え、test_retry が落ちる
cd "$1"
git merge -q -X ours feature/retry -m "Merge branch 'feature/retry'" >/dev/null 2>&1

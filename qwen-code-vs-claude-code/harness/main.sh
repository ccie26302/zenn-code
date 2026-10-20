#!/bin/bash
# 本測定: C・Q・L × 全43課題 × 3回。構成をまたいでシード固定でシャッフルし、1本ずつ流す
# (Google Cloud の対象のプロジェクトと出口の切り替えを共有するので並列にしない。時間帯による API の速さの揺れが構成に偏らないよう混ぜる)
cd "$(dirname "$0")"
TASKS=$(cd ../tasks && ls -d [MDGTR]*_[0-9]* | sort)
SPEC=""; for t in $TASKS; do for c in C Q L; do SPEC="$SPEC $c:${t}:3"; done; done
RUN_TAG= ./run_set.sh main 20261022 $SPEC

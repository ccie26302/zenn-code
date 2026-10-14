#!/bin/bash
# usage: dock.sh setup|judge|solve|nearmiss TASK_ID WORKDIR
# どれもネットワークなしのコンテナで動かす(エージェントと同じイメージ)
set -e
MODE=$1; T=$2; W=$3
TR="$(cd "$(dirname "$0")" && pwd)"
case $MODE in
  setup)    CMD="python3 /tasks/$T/setup.py /work" ;;
  judge)    CMD="python3 /tasks/$T/judge.py /work" ; RO=":ro" ;;
  solve)    CMD="bash /tasks/$T/solve.sh /work" ;;
  nearmiss) CMD="bash /tasks/$T/nearmiss.sh /work" ;;
esac
docker run --rm --network none -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0='*' \
  -v "$TR:/tasks:ro" -v "$W:/work$RO" argon-agent bash -c "$CMD"

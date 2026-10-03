#!/bin/zsh
# 最終比較(PLAN.md「最終比較」と「最終比較の修正」)。全本英語。
cd "$(dirname "$0")/.." && mkdir -p logs
python3 harness/probe_models_en.py > logs/probe_models_en.log 2>&1
cd harness
C="POLICY=systemone ACTSET=v3 MEMORY=gain ALPHA=0.5 GAMMA=1.0 STATKEY=coarse GAIN=net NOBAN=1 SOFTPEN=50 STATE_V=4 GOAL_X=640 REC=1 REC_ALL=1 EP=100 STEPS=80 LANG_=en"
M="POLICY=systemone ACTSET=v3 MEMORY=ban NOBAN=1 STATE_V=4 REC=1 REC_ALL=1 EP=30 STEPS=80 LANG_=en"
KEV="MODEL_URL=http://127.0.0.1:8009/v1/systemone"; LAYA="MODEL_URL=http://127.0.0.1:8078/v1/systemone"
run() { local tag=$1; shift; env "$@" TAG=$tag node run_play.mjs > ../logs/$tag.log 2>&1; }
run fin_kev_en_1  ${=C} $KEV
run fin_laya_en_1 ${=C} $LAYA
run fin_kev_en_modelonly  ${=M} $KEV
run fin_laya_en_modelonly ${=M} $LAYA
run fin_kev_en_2  ${=C} $KEV
run fin_laya_en_2 ${=C} $LAYA
run fin_kev_en_3  ${=C} $KEV
run fin_laya_en_3 ${=C} $LAYA
echo done > ../logs/chain_final.done

# 判定の準備(エージェントと同じ権限で動かす): 既にある状態で1回 → 2つを消して1回 → もう1回。終了コードを記録する
rc=(); [ -f create_infra.sh ] || { echo '{"missing":true}' > .idem_result.json; exit 0; }
bash create_infra.sh >/dev/null 2>&1; rc+=($?)
gcloud storage rm -r gs://qg-$ID-app -q >/dev/null 2>&1; gcloud iam service-accounts delete qg-$ID-app@$P.iam.gserviceaccount.com --project $P -q >/dev/null 2>&1; sleep 20
bash create_infra.sh >/dev/null 2>&1; rc+=($?); sleep 10
bash create_infra.sh >/dev/null 2>&1; rc+=($?)
echo "{\"rc\": [${rc[0]}, ${rc[1]}, ${rc[2]}]}" > .idem_result.json

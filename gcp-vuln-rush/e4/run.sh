#!/bin/bash
# E4: API の手前で認証を確かめる(各3回)。usage: e4/run.sh LABEL(authz_off / authz_on)
cd "$(dirname "$0")"; P=$(cat ../project.txt); L=$1
GW=https://$(gcloud api-gateway gateways describe sec2-gw --location asia-northeast1 --project $P --format='value(defaultHostname)')
RUN=$(gcloud run services describe e4-api --project $P --region asia-northeast1 --format='value(status.url)')
tok(){ gcloud auth print-identity-token --impersonate-service-account=$1@$P.iam.gserviceaccount.com --audiences=$2 --include-email 2>/dev/null; }
A=$(tok e4-alice sec2-api); AW=$(tok e4-alice other-api)
AT=$(python3 -c "import sys;t=sys.argv[1].split('.');s=t[2];t[2]=('A' if s[5]!='A' else 'B')+s[1:] if False else s[:5]+('A' if s[5]!='A' else 'B')+s[6:];print('.'.join(t))" "$A")
[ -f ../results/e4_auth.csv ] || echo "label,case,rep,http,body" > ../results/e4_auth.csv
c(){ local name=$1; shift; for i in 1 2 3; do r=$(curl -s -m 30 -w '\n%{http_code}' "$@"); code=$(echo "$r" | tail -1); body=$(echo "$r" | sed '$d' | tr -d ',\n' | cut -c1-120); echo "$L,$name,$i,$code,$body" >> ../results/e4_auth.csv; done; }
c "Cloud Run を直接・トークンなし" "$RUN/orders?user=alice"
c "ゲートウェイ・トークンなし" "$GW/orders?user=alice"
c "ゲートウェイ・署名を1文字変えたトークン" -H "Authorization: Bearer $AT" "$GW/orders?user=alice"
c "ゲートウェイ・別の宛先(audience)のトークン" -H "Authorization: Bearer $AW" "$GW/orders?user=alice"
c "ゲートウェイ・alice のトークンで alice のデータ" -H "Authorization: Bearer $A" "$GW/orders?user=alice"
c "ゲートウェイ・alice のトークンで bob のデータ" -H "Authorization: Bearer $A" "$GW/orders?user=bob"

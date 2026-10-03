#!/bin/zsh
# ネットワークだけの往復(推論なし)。新しい接続ごとに DNS / TCP 接続 / TLS / 最初の応答までを curl で測る。usage: bench/net.sh <host> [N=50]
H=$1; N=${2:-50}; OUT=data/bench/net_${H//./_}_$(date +%Y%m%d-%H%M%S).csv
echo "i,dns_ms,tcp_ms,tls_ms,ttfb_ms,total_ms,http" > $OUT
for i in $(seq 1 $N); do
  curl -s -o /dev/null -w "$i,%{time_namelookup},%{time_connect},%{time_appconnect},%{time_starttransfer},%{time_total},%{http_code}\n" "https://$H/" \
   | awk -F, '{printf "%s,%.2f,%.2f,%.2f,%.2f,%.2f,%s\n",$1,$2*1000,($3-$2)*1000,($4-$3)*1000,$5*1000,$6*1000,$7}' >> $OUT
  sleep 0.2
done
python3 - $OUT <<'PY'
import csv,sys
R=list(csv.DictReader(open(sys.argv[1])))
for k in ("dns_ms","tcp_ms","tls_ms","ttfb_ms"):
    v=sorted(float(r[k]) for r in R); print(k,"p50",v[len(v)//2],"p90",v[int(len(v)*.9)])
print(sys.argv[1])
PY

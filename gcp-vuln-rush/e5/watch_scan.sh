#!/bin/bash
# E2: スキャンが今回の CVE を出すようになる時刻を30分ごとに記録する
cd "$(dirname "$0")"; P=$(cat ../project.txt); R=asia-northeast1-docker.pkg.dev/$P/e2
[ -f ../results/e5_scan_watch.csv ] || echo "utc,image,total_vulns,php_cve_hits" > ../results/e5_scan_watch.csv
while true; do
  for i in e5-py-old:1 e5-py-new:1 e5-go-old:1 e5-go-new:1; do
    gcloud artifacts docker images describe $R/$i --show-package-vulnerability --format=json 2>/dev/null | python3 -c "
import sys,json,time
d=json.load(sys.stdin); v=d.get('package_vulnerability_summary',{}).get('vulnerabilities',{})
n=sum(len(a) for a in v.values()); hits=[o.get('noteName','').split('/')[-1] for a in v.values() for o in a if any(x in o.get('noteName','') for x in ('96639','96640','112398','6809','91403'))]
print('%s,%s,%d,%s' % (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), '$i', n, '|'.join(sorted(set(hits)))))" >> ../results/e5_scan_watch.csv
  done
  sleep 1200
done

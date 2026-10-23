#!/bin/bash
# E2: スキャンが今回の CVE を出すようになる時刻を30分ごとに記録する
cd "$(dirname "$0")"; P=$(cat ../project.txt); R=asia-northeast1-docker.pkg.dev/$P/e2
[ -f ../results/e2_scan_watch.csv ] || echo "utc,image,total_vulns,php_cve_hits" > ../results/e2_scan_watch.csv
while true; do
  for i in php-apt-ubu-old:1 php-apt-ubu:1 php-apt-deb:1 php:8.4.25-apache php:8.4.26-apache php:8.4.27-apache; do
    gcloud artifacts docker images describe $R/$i --show-package-vulnerability --format=json 2>/dev/null | python3 -c "
import sys,json,time
d=json.load(sys.stdin); v=d.get('package_vulnerability_summary',{}).get('vulnerabilities',{})
n=sum(len(a) for a in v.values()); hits=[o.get('noteName','').split('/')[-1] for a in v.values() for o in a if '10961' in o.get('noteName','')]
print('%s,%s,%d,%s' % (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), '$i', n, '|'.join(sorted(set(hits)))))" >> ../results/e2_scan_watch.csv
  done
  sleep 1800
done

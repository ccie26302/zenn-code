# 惜しい誤答: 1ページ目だけを抜き出す
cd "$1" && pdftotext -layout -l 1 invoice.pdf - | python3 -c "
import re, sys, csv
w = csv.writer(open('items.csv', 'w', newline='')); w.writerow(['sku','description','qty','unit_price','amount'])
for l in sys.stdin:
    m = re.match(r'(SKU-\d+)\s+(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s*$', l.strip())
    if m: w.writerow([m.group(1), m.group(2), m.group(3), m.group(4).replace(',', ''), m.group(5).replace(',', '')])
"

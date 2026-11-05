#!/bin/bash
# Reproduce the dataset. Requires python3 and network access to sec.gov.
# 1) download submissions index + earnings releases / 10-Q / 10-K text into raw/
# 2) write data/financials.csv from hand-extracted values (each value can be grepped in raw/*.txt)
# 3) compute data/derived.csv (needs data/market_share.csv for the Synergy columns)
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
UA="YOUR_NAME your-email@example.com"
mkdir -p "$D/raw" "$D/data"
for c in 0001652044:GOOGL 0001018724:AMZN 0000789019:MSFT 0001341439:ORCL; do
  curl -s -A "$UA" "https://data.sec.gov/submissions/CIK${c%%:*}.json" -o "$D/raw/sub_${c##*:}.json"; sleep 0.3
done
python3 -I "$D/scripts/fetch_sec.py" "$D/raw"
python3 -I "$D/scripts/build_financials.py" "$D"
python3 -I "$D/scripts/build_market_share.py" "$D"
python3 -I "$D/scripts/derive.py" "$D"
python3 -I "$D/scripts/build_timeline.py" "$D"
# spot checks (should print the Google Cloud revenue / operating income rows of the Q3 2026 release)
grep -E "^ ?Google Cloud \|" "$D/raw/GOOGL_8-K_2026-10-28_2026-10-28.txt" | head -2

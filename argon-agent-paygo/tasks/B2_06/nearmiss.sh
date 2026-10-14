#!/bin/bash
# 惜しい誤答: 動かすことはできたが、README は init-db だけ直して export の手順を直し忘れる
cd "$1"
python3 manage.py initdb && python3 manage.py import data/sales.csv && python3 manage.py export --out out/summary.json
sed -i -e 's/manage.py init-db/manage.py initdb/' README.md

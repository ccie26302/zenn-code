#!/bin/bash
cd "$1"
python3 manage.py initdb && python3 manage.py import data/sales.csv && python3 manage.py export --out out/summary.json
sed -i -e 's/manage.py init-db/manage.py initdb/' -e 's#manage.py export out/summary.json#manage.py export --out out/summary.json#' README.md

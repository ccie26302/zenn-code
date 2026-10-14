#!/bin/bash
# 惜しい誤答: 仮想環境は作ったが、build.py をシステムの Python で(PYTHONPATH を通して)動かす
cd "$1"
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
PYTHONPATH=$(ls -d .venv/lib/python3*/site-packages) python3 build.py

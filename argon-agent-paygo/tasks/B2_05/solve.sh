#!/bin/bash
cd "$1"
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt && .venv/bin/python build.py

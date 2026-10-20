#!/bin/sh
# モデルの中継(8080)と受け口(9000)と、Google Cloud への出口(3128、mitmproxy)
python3 -u /proxy.py &
exec mitmdump -q --listen-port 3128 --set confdir=/mitm --set block_global=false -s /gcp_addon.py

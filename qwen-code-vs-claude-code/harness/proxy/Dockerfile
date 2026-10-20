FROM python:3.13-slim
RUN pip install --no-cache-dir mitmproxy==11.1.3
COPY proxy.py gcp_addon.py start.sh /
CMD ["/bin/sh", "/start.sh"]

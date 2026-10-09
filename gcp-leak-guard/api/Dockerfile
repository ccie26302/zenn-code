FROM python:3.12-slim
# 修正版が出ているものを、ベースイメージの公開を待たずに取り込む(週次の再ビルドで毎回効く)
# - OS パッケージを更新する
# - イメージに同梱された pip を更新し、実行時に使わない ensurepip の同梱 wheel(古い pip)を消す
RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir --upgrade pip \
 && rm -f /usr/local/lib/python3.12/ensurepip/_bundled/pip-*.whl
WORKDIR /app
RUN pip install --no-cache-dir flask==3.1.* gunicorn==23.*
COPY main.py .
CMD exec gunicorn -b :$PORT main:app

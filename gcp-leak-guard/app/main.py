"""検証用の最小アプリ。値そのものは返さない(長さだけ)。"""
import os
from flask import Flask, jsonify
from google.cloud import secretmanager

app = Flask(__name__)
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")


@app.get("/")
def index():
    return "ok\n"


@app.get("/secret/<name>")
def read_secret(name):
    """実行用 SA が読める secret だけ読める(最小権限の確認用)。値は返さず長さだけ返す。"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        v = client.access_secret_version(name=f"projects/{PROJECT}/secrets/{name}/versions/latest")
        return jsonify(secret=name, readable=True, length=len(v.payload.data))
    except Exception as e:  # noqa: BLE001
        return jsonify(secret=name, readable=False, error=type(e).__name__), 403

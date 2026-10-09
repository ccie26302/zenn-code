"""API の例(Cloud Armor のレートリミットの確認用)。ID は UUID で、連番にしない。"""
import uuid
from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/items/<item_id>")
def item(item_id):
    try:
        uuid.UUID(item_id)
    except ValueError:
        return jsonify(error="invalid id"), 400
    return jsonify(id=item_id, name="sample")

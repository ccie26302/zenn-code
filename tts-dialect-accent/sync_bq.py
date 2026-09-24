"""BigQuery の記録を data/requests.jsonl に写す"""
import json, os
from google.cloud import bigquery
HERE = os.path.dirname(os.path.abspath(__file__))
rows = bigquery.Client(project=os.environ["PROJECT_ID"]).query(
    f"SELECT * FROM `{os.environ['BQ_TABLE']}` ORDER BY req").result()
with open(os.path.join(HERE, "data", "requests.jsonl"), "w") as f:
    for r in rows:
        d = dict(r)
        for k in ("errors", "words"):
            if isinstance(d.get(k), str) and d[k][:1] in "[{": d[k] = json.loads(d[k])
        if d.get("at"): d["at"] = d["at"].isoformat()
        f.write(json.dumps(d, ensure_ascii=False) + "\n")
print("synced")

"""計画どおりに TTS を呼び、WAV と記録を残す（PLAN.md 4節）。

使い方: python synth.py <段階>   段階 = gate / main / repeat / q2
  - GCS_BUCKET があれば WAV を gs://<bucket>/wav/ へ、なければ data/wav/ へ
  - BQ_TABLE があれば記録を BigQuery へ、常に data/requests.jsonl にも追記
  - API キーは環境変数 GEMINI_API_KEY（Cloud Run では Secret Manager から注入）
  - 既に成功したリクエスト番号は飛ばす。出力は最初の成功を使い、作り直さない
"""
import os, sys, json, time, base64, datetime
from google import genai
import corpus as C

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "data", "requests.jsonl")
BUCKET = os.environ.get("GCS_BUCKET"); BQ = os.environ.get("BQ_TABLE")
MODEL = "gemini-3.8-flash-tts"; GAP = 20; MAX_TRY = 12

def done_reqs():
    out = set()
    if os.path.exists(LOG):
        for l in open(LOG):
            r = json.loads(l)
            if r.get("ok"): out.add(r["req"])
    if BQ:
        from google.cloud import bigquery
        try:
            out |= {row.req for row in bigquery.Client().query(f"SELECT req FROM `{BQ}` WHERE ok").result()}
        except Exception: pass
    return out

def save(name, data):
    if BUCKET:
        from google.cloud import storage
        storage.Client().bucket(BUCKET).blob("wav/" + name).upload_from_string(data, content_type="audio/wav")
        return f"gs://{BUCKET}/wav/{name}"
    p = os.path.join(HERE, "data", "wav", name); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(data); return p

def record(rec):
    with open(LOG, "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if BQ:
        from google.cloud import bigquery
        errs = bigquery.Client().insert_rows_json(BQ, [{k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
                                                        for k, v in rec.items()}])
        if errs: print("BigQuery への書き込みに失敗:", errs, flush=True)

def call(cl, voice, style, text):
    item = {"type": "text", "text": text}
    if style: item["annotations"] = [{"type": "speech_metadata", "style": style}]
    it = cl.interactions.create(model=MODEL, input=[{"type": "user_input", "content": [item]}],
                                response_format={"type": "audio"}, generation_config={"speech_config": [{"voice": voice}]})
    return base64.b64decode(it.output_audio.data), getattr(it, "model", None)

def main(stage):
    cl = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    done = done_reqs()
    todo = [p for p in C.PLANNED if p["stage"] == stage and p["req"] not in done]
    print(f"{stage}: {len(todo)} 件", flush=True)
    for p in todo:
        if p["frame"] == "long": text, words = C.LONG_TEXT, None
        else: text, words = C.request_text(p["frame"], p["seed"])
        style = C.STYLES[p["style"]]
        errors = []
        for k in range(MAX_TRY):
            t0 = time.time()
            try:
                wav, model = call(cl, p["voice"], style, text)
                uri = save(f"req{p['req']:03d}.wav", wav)
                rec = dict(p, ok=True, attempts=k + 1, errors=errors, model=model, ms=round((time.time() - t0) * 1000),
                           bytes=len(wav), uri=uri, words=words, text=text, style_text=style,
                           at=datetime.datetime.now(datetime.timezone.utc).isoformat())
                record(rec); print(f"  req{p['req']:03d} {p['voice']} {p['style']} OK ({k+1}回目)", flush=True)
                break
            except Exception as e:
                msg = str(e)[:400]; errors.append(msg); print(f"  req{p['req']:03d} 失敗: {msg[:120]}", flush=True)
                time.sleep(60 if "429" in msg or "RESOURCE_EXHAUSTED" in msg else 20)
        else:
            record(dict(p, ok=False, attempts=MAX_TRY, errors=errors))
        time.sleep(GAP)

if __name__ == "__main__":
    main(sys.argv[1])

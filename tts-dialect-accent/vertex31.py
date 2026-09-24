"""Q4（参考）：Google Cloud の Cloud Text-to-Speech で使える Gemini-TTS 3.1 Flash preview に同じ関西の枠を読ませる。
3.1 には大阪ラベルの声が無いので、プリセット声（Kore・Charon）× 指示（K / N）。"""
import os, json, time, datetime, corpus as C
from google.cloud import texttospeech as tts
from google.api_core.client_options import ClientOptions
HERE = os.path.dirname(os.path.abspath(__file__))
cl = tts.TextToSpeechClient(client_options=ClientOptions(quota_project_id=os.environ["PROJECT_ID"]))
PLAN = [(901, "Kore", "K"), (902, "Kore", "N"), (903, "Charon", "K"), (904, "Charon", "N")]
log = os.path.join(HERE, "data", "vertex31.jsonl")
done = {json.loads(l)["req"] for l in open(log)} if os.path.exists(log) else set()
for req, voice, st in PLAN:
    if req in done: continue
    text, words = C.request_text("kansai", 20260925 + req)
    t0 = time.time()
    r = cl.synthesize_speech(input=tts.SynthesisInput(text=text.replace(" <long pause> ", "\n"), prompt=C.STYLES[st] or None),
        voice=tts.VoiceSelectionParams(language_code="ja-JP", name=voice, model_name="gemini-3.1-flash-tts-preview"),
        audio_config=tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16, sample_rate_hertz=24000))
    p = os.path.join(HERE, "data", "wav", f"req{req:03d}.wav"); open(p, "wb").write(r.audio_content)
    rec = dict(req=req, stage="vertex31", voice=voice, style=st, frame="kansai", seed=20260925 + req, ok=True, attempts=1,
               model="gemini-3.1-flash-tts-preview", ms=round((time.time() - t0) * 1000), words=words, text=text,
               at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    open(log, "a").write(json.dumps(rec, ensure_ascii=False) + "\n"); print(req, voice, st, "OK", rec["ms"], "ms", flush=True)

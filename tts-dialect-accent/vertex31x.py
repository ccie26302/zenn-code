"""14節：Cloud Text-to-Speech の Gemini-TTS 3.1 Flash preview を、6声×3条件×2回で測る。"""
import os, json, time, datetime, corpus as C
from google.cloud import texttospeech as tts
from google.api_core.client_options import ClientOptions
HERE = os.path.dirname(os.path.abspath(__file__))
cl = tts.TextToSpeechClient(client_options=ClientOptions(quota_project_id=os.environ["PROJECT_ID"]))
VOICES = ["Algenib", "Algieba", "Callirrhoe", "Erinome", "Leda", "Sulafat"]
CONDS = [("N", "standard"), ("N", "kansai"), ("K", "kansai")]
log = os.path.join(HERE, "data", "vertex31.jsonl")
done = {json.loads(l)["req"] for l in open(log)}
req = 1000
for v in VOICES:
    for st, fr in CONDS:
        seed = 20260927 + len(VOICES) * 10 + VOICES.index(v) * 3 + CONDS.index((st, fr))
        for rep in (1, 2):
            req += 1
            if req in done: continue
            text, words = C.request_text(fr, seed)
            t0 = time.time()
            r = cl.synthesize_speech(input=tts.SynthesisInput(text=text.replace(" <long pause> ", "\n"), prompt=C.STYLES[st] or None),
                voice=tts.VoiceSelectionParams(language_code="ja-JP", name=v, model_name="gemini-3.1-flash-tts-preview"),
                audio_config=tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16, sample_rate_hertz=24000))
            open(os.path.join(HERE, "data", "wav", f"req{req:04d}.wav"), "wb").write(r.audio_content)
            rec = dict(req=req, stage="vertex31x", voice=v, style=st, frame=fr, seed=seed, rep=rep, ok=True, attempts=1,
                       model="gemini-3.1-flash-tts-preview", ms=round((time.time() - t0) * 1000), chars=len(text), words=words, text=text,
                       at=datetime.datetime.now(datetime.timezone.utc).isoformat())
            open(log, "a").write(json.dumps(rec, ensure_ascii=False) + "\n"); print(req, v, st, fr, rep, rec["ms"], "ms", flush=True)

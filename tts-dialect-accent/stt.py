"""Speech-to-Text v2 (Chirp 3) で書き起こし、語ごとの時刻を返す。
同期認識は60秒までなので、50秒を超える音声は無音に近い位置で分割し、時刻をつなぎ直す。"""
import os, io, numpy as np, soundfile as sf
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech as cs
from google.api_core.client_options import ClientOptions
PROJECT = os.environ["PROJECT_ID"]; LOC = "us"
_cl = SpeechClient(client_options=ClientOptions(api_endpoint=f"{LOC}-speech.googleapis.com"))

def _recognize(wav_bytes):
    cfg = cs.RecognitionConfig(auto_decoding_config=cs.AutoDetectDecodingConfig(), language_codes=["ja-JP"],
                               model="chirp_3", features=cs.RecognitionFeatures(enable_word_time_offsets=True))
    r = _cl.recognize(request=cs.RecognizeRequest(recognizer=f"projects/{PROJECT}/locations/{LOC}/recognizers/_",
                                                  config=cfg, content=wav_bytes))
    text = ""; words = []
    for res in r.results:
        a = res.alternatives[0]; text += a.transcript
        words += [(w.word, w.start_offset.total_seconds(), w.end_offset.total_seconds()) for w in a.words]
    return text, words

def _cut_points(x, sr, max_len=50.0):
    cuts = [0]; fr = int(0.01 * sr)
    while (len(x) - cuts[-1]) / sr > max_len:
        lo = cuts[-1] + int((max_len - 10) * sr); hi = cuts[-1] + int(max_len * sr)
        e = [np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(lo, hi, fr)]
        cuts.append(lo + int(np.argmin(e)) * fr)
    return cuts + [len(x)]

def transcribe(wav_bytes):
    x, sr = sf.read(io.BytesIO(wav_bytes))
    cuts = _cut_points(x, sr); text = ""; words = []
    for a, b in zip(cuts, cuts[1:]):
        buf = io.BytesIO(); sf.write(buf, x[a:b], sr, format="WAV", subtype="PCM_16")
        t, w = _recognize(buf.getvalue()); off = a / sr
        text += t; words += [(ww, s + off, (e + off) if e > 0 else 0.0) for ww, s, e in w]
    return text, words

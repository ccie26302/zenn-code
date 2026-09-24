"""Speech-to-Text v2 (Chirp 3) で書き起こし、語ごとの時刻を返す。"""
import os
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech as cs
from google.api_core.client_options import ClientOptions
PROJECT = os.environ["PROJECT_ID"]; LOC = "us"
_cl = SpeechClient(client_options=ClientOptions(api_endpoint=f"{LOC}-speech.googleapis.com"))
def transcribe(wav_bytes):
    cfg = cs.RecognitionConfig(auto_decoding_config=cs.AutoDetectDecodingConfig(), language_codes=["ja-JP"],
                               model="chirp_3", features=cs.RecognitionFeatures(enable_word_time_offsets=True))
    r = _cl.recognize(request=cs.RecognizeRequest(recognizer=f"projects/{PROJECT}/locations/{LOC}/recognizers/_",
                                                  config=cfg, content=wav_bytes))
    text = ""; words = []
    for res in r.results:
        a = res.alternatives[0]; text += a.transcript
        words += [(w.word, w.start_offset.total_seconds(), w.end_offset.total_seconds()) for w in a.words]
    return text, words

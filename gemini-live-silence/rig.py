"""測定リグ(レビュー指摘反映版)。

反映した指摘:
 - 体感無音は再生カーソルで算出(到着ギャップではない)。バイト長を必ず記録
 - TTFA / 実質回答の開始 / 完了 を別指標として分離
 - 固定sleepの打ち切りをやめ turn_complete 待ち + ハードタイムアウト。censored を記録
 - 例外は握り潰さない。ok / err を全行に記録(失敗行も必ず書く)
 - interrupted を記録
 - 条件はブロック内シャッフル(seed固定)。trial_index/block_index/wall_clock/seed/sdk を記録
 - 音声WAVを試行ごとに保存(事後に波形から再計算できるように)
"""
import asyncio, os, time, wave, contextlib, json
from importlib.metadata import version
import numpy as np
from google import genai
from google.genai import types

HERE = os.path.dirname(os.path.abspath(__file__))
SDK = version("google-genai")
SR_OUT = 24000
BYTES_PER_MS = SR_OUT * 2 / 1000.0      # 24kHz mono 16bit → 48 byte/ms

def client():
    return genai.Client(api_key=open(os.path.join(HERE, ".aistudio.key")).read().strip())

class Trace:
    """1試行ぶんの観測。到着時刻とバイト長を必ず対で持つ。"""
    def __init__(self, t0):
        self.t0 = t0
        self.audio = []        # (arrival_ms, nbytes)
        self.blobs = []        # bytes
        self.events = []       # (ms, kind, text)
    def ms(self): return round((time.perf_counter() - self.t0) * 1000)
    def add(self, kind, text=""): self.events.append((self.ms(), kind, text))

    # --- 派生指標 ---
    def ttfa(self):
        return self.audio[0][0] if self.audio else None
    def play_ms(self):
        return sum(n for _, n in self.audio) / BYTES_PER_MS
    def playout(self):
        """実際に音が鳴っている区間 [(開始ms, 終了ms)] を再生カーソルで構成する。"""
        out, cur = [], None
        for at, n in self.audio:
            st = max(at, cur) if cur is not None else at
            en = st + n / BYTES_PER_MS
            if out and st <= out[-1][1] + 1e-6:
                out[-1] = (out[-1][0], en)
            else:
                out.append((st, en))
            cur = en
        return out

    def perceived_silences(self):
        """再生カーソル基準の無音区間 [(開始ms, 長さms)]。冒頭の無音は含めない。"""
        p = self.playout()
        return [(p[i][1], p[i+1][0] - p[i][1]) for i in range(len(p)-1) if p[i+1][0] > p[i][1]]

    def silence_in(self, t_start, t_end):
        """[t_start, t_end] のあいだ、音が鳴っていない最長の連続区間(ms)。
        区間内に音が一切無ければ区間全体が無音として返る(0にならない)。"""
        if t_start is None or t_end is None or t_end <= t_start: return None
        busy = [(max(a, t_start), min(b, t_end)) for a, b in self.playout() if b > t_start and a < t_end]
        worst, cur = 0.0, t_start
        for a, b in busy:
            if a > cur: worst = max(worst, a - cur)
            cur = max(cur, b)
        return max(worst, t_end - cur)
    def max_silence(self):
        s = self.perceived_silences()
        return max((d for _, d in s), default=0.0)
    def said(self):
        return "".join(t for _, k, t in self.events if k == "say")
    def first_say(self):
        return next(((m, t) for m, k, t in self.events if k == "say"), (None, ""))
    def n(self, kind):
        return sum(1 for _, k, _ in self.events if k == kind)
    def save_wav(self, path):
        if not self.blobs: return None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR_OUT)
            w.writeframes(b"".join(self.blobs))
        return path

async def pump(session, tr, on_tool=None):
    """receive() は1ターンで終わるので張り直し続ける。例外は投げる(握り潰さない)。"""
    while True:
        async for m in session.receive():
            sc = m.server_content
            if sc:
                if sc.model_turn:
                    for p in sc.model_turn.parts:
                        if p.inline_data and p.inline_data.data:
                            tr.audio.append((tr.ms(), len(p.inline_data.data)))
                            tr.blobs.append(p.inline_data.data)
                        if getattr(p, "thought", None):
                            tr.add("thought", str(p.text or "")[:80])
                if sc.input_transcription and sc.input_transcription.text:
                    tr.add("heard", sc.input_transcription.text)
                if sc.output_transcription and sc.output_transcription.text:
                    tr.add("say", sc.output_transcription.text)
                if sc.interrupted: tr.add("interrupted")
                if sc.generation_complete: tr.add("gen_complete")
                if sc.turn_complete: tr.add("turn_complete")
            if m.tool_call and on_tool:
                for fc in m.tool_call.function_calls:
                    tr.add("tool_call", fc.name)
                    asyncio.create_task(on_tool(fc))
            if m.go_away: tr.add("go_away", str(m.go_away)[:60])

async def ask(model, cfg, prompt, *, timeout=30.0, quiet_ms=1500, on_tool=None, wav=None):
    """1試行。turn_complete + 無音継続で完了とみなす。打ち切りは censored=1。"""
    c = client()
    rec = dict(model=model, sdk=SDK, prompt=prompt, ok=0, err="", censored=0,
               wall_clock=time.strftime("%Y-%m-%dT%H:%M:%S"))
    t_conn = time.perf_counter()
    try:
        async with c.aio.live.connect(model=model, config=cfg) as s:
            t0 = time.perf_counter()
            tr = Trace(t0)
            task = asyncio.create_task(pump(s, tr, on_tool))
            await s.send_client_content(
                turns=types.Content(role="user", parts=[types.Part(text=prompt)]),
                turn_complete=True)
            t_sent = time.perf_counter()
            deadline = t_sent + timeout
            while time.perf_counter() < deadline:
                if task.done():
                    task.result()                    # 例外があればここで出る
                    break
                if tr.n("turn_complete") >= 1 and tr.audio:
                    # 最後の音声が届いてから quiet_ms 静かなら完了
                    last = tr.audio[-1][0] + tr.audio[-1][1] / BYTES_PER_MS
                    if tr.ms() - last > quiet_ms: break
                await asyncio.sleep(0.02)
            else:
                rec["censored"] = 1
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError): await task
    except Exception as e:
        rec["err"] = "%s: %s" % (type(e).__name__, str(e)[:120])
        return rec, None
    fs_ms, fs_tx = tr.first_say()
    rec.update(ok=1 if tr.audio else 0,
               connect_ms=round((t0 - t_conn) * 1000),
               ttfa_ms=tr.ttfa(),
               first_say_ms=fs_ms, first_say=fs_tx[:60],
               play_ms=round(tr.play_ms()),
               max_silence_ms=round(tr.max_silence()),
               n_interrupted=tr.n("interrupted"),
               n_turn_complete=tr.n("turn_complete"),
               n_thought=tr.n("thought"),
               said=tr.said()[:300])
    if wav: tr.save_wav(wav)
    return rec, tr

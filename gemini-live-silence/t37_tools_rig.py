"""E5本測定: 音声エージェントのツール沈黙。

事前登録:
  主要エンドポイント = ツール所要6秒における「体感の最大無音(ms)」の
                      nb_progress vs blocking。これだけが確認的検定。
  それ以外(他のdelay, nb_silent, 副次指標)は探索的。
予測:
  blocking は沈黙 ≒ ツール所要。nb_progress は大幅に短い。
  nb_silent は blocking と差がない(=効いているのは進捗であって behavior ではない)。
"""
import asyncio, os, sys, csv, random, time, contextlib
from google.genai import types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig
HERE = os.path.dirname(os.path.abspath(__file__))

SYS = ("あなたは運用担当のアシスタントです。サーバの状況を聞かれたら check_server_status を呼び、"
       "途中経過が届いたらその都度ひとこと声に出して伝えてください。"
       "最終結果が届いたら、状態・CPU使用率・稼働日数を必ず読み上げてください。日本語で簡潔に。")
PROMPT = "本番サーバ web-01 の状況を確認して。"
RESULT = {"status": "正常", "cpu": "32%", "uptime": "14日"}

def cfg(mode, level=None):
    fd = types.FunctionDeclaration(
        name="check_server_status", description="サーバの稼働状況を調べる。時間がかかる。",
        parameters=types.Schema(type="OBJECT",
            properties={"server": types.Schema(type="STRING")}, required=["server"]))
    if mode.startswith("nb"): fd.behavior = types.Behavior.NON_BLOCKING
    c = types.LiveConnectConfig(
        response_modalities=["AUDIO"], system_instruction=SYS,
        tools=[types.Tool(function_declarations=[fd])],
        output_audio_transcription=types.AudioTranscriptionConfig())
    if level: c.thinking_config = types.ThinkingConfig(thinking_level=level)
    return c

def _norm(t):
    """漢数字の読み上げを数字に寄せる(判定用)。"""
    import re
    K={"〇":"0","一":"1","二":"2","三":"3","四":"4","五":"5","六":"6","七":"7","八":"8","九":"9"}
    def tens(m):
        a,b=m.group(1),m.group(2)
        return str((int(K[a]) if a else 1)*10 + (int(K[b]) if b else 0))
    t=re.sub(r"([一二三四五六七八九])?十([一二三四五六七八九])?", tens, t)
    for k,v in K.items(): t=t.replace(k,v)
    return t

async def trial(model, mode, delay, level=None, wav=None, timeout=45.0, prog_every=1.5,
                use_scheduling=True):
    c = rig.client()
    rec = dict(model=model, mode=mode, delay_s=delay, level=level or "", sdk=rig.SDK,
               ok=0, err="", censored=0, wall_clock=time.strftime("%Y-%m-%dT%H:%M:%S"))
    try:
        async with c.aio.live.connect(model=model, config=cfg(mode, level)) as s:
            t0 = time.perf_counter(); tr = rig.Trace(t0)
            final_sent = asyncio.Event()
            async def on_tool(fc):
                if mode == "nb_progress":
                    steps = [(i+1)*prog_every for i in range(int(delay/prog_every)) if (i+1)*prog_every < delay]
                    prev = 0.0
                    for t in steps:
                        await asyncio.sleep(t-prev); prev = t
                        tr.add("progress", "調査中(%.1fs)" % t)
                        with contextlib.suppress(Exception):
                            fr = types.FunctionResponse(id=fc.id, name=fc.name,
                                    will_continue=True, response={"output": "調査中です"})
                            if use_scheduling:
                                fr.scheduling = types.FunctionResponseScheduling.WHEN_IDLE
                            await s.send_tool_response(function_responses=[fr])
                    await asyncio.sleep(max(0.0, delay-prev))
                else:
                    await asyncio.sleep(delay)
                tr.add("final_sent")
                fr = types.FunctionResponse(id=fc.id, name=fc.name, response={"output": RESULT})
                if mode.startswith("nb"):
                    fr.will_continue = False
                    if use_scheduling:
                        fr.scheduling = types.FunctionResponseScheduling.INTERRUPT
                with contextlib.suppress(Exception):
                    await s.send_tool_response(function_responses=[fr])
                final_sent.set()
            task = asyncio.create_task(rig.pump(s, tr, on_tool))
            await s.send_client_content(
                turns=types.Content(role="user", parts=[types.Part(text=PROMPT)]), turn_complete=True)
            dl = time.perf_counter() + timeout
            while time.perf_counter() < dl:
                if task.done(): task.result(); break
                if final_sent.is_set():
                    fsm = next((m for m,k,_ in tr.events if k=="final_sent"), None)
                    # 最終結果を送った「後」に新しく音声が始まるまで待つ
                    after = [at for at,_ in tr.audio if fsm is not None and at >= fsm]
                    if after:
                        last = tr.audio[-1][0] + tr.audio[-1][1]/rig.BYTES_PER_MS
                        if tr.ms() - last > 1500: break
                await asyncio.sleep(0.02)
            else:
                rec["censored"] = 1
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError): await task
    except Exception as e:
        rec["err"] = "%s: %s" % (type(e).__name__, str(e)[:110]); return rec
    tc = next((m for m,k,_ in tr.events if k=="tool_call"), None)
    fs = next((m for m,k,_ in tr.events if k=="final_sent"), None)
    ans = next((at for at,_ in tr.audio if fs is not None and at >= fs), None)   # 最終回答の開始
    gap = tr.silence_in(tc, ans) if (tc is not None and ans is not None) else None
    said = tr.said()
    rec.update(ok=1 if tr.audio else 0,
               ttfa_ms=tr.ttfa(), tool_call_ms=tc, final_sent_ms=fs,
               max_silence_ms=round(tr.max_silence()),
               tool_gap_ms=(round(gap) if gap is not None else ""),
               no_answer=int(ans is None),
               answer_start_ms=ans,
               answer_latency_ms=(round(ans-fs) if (ans is not None and fs is not None) else ""),
               play_ms=round(tr.play_ms()),
               play_in_tool_ms=round(sum(n for at,n in tr.audio if tc and fs and tc<=at<=fs)/rig.BYTES_PER_MS),
               n_progress=tr.n("progress"), n_interrupted=tr.n("interrupted"),
               answer_ok=int(("正常" in said) and ("32" in _norm(said)) and ("14" in _norm(said))),
               leaked=int(("<tool_code>" in said) or ("<actions>" in said) or ("print(" in said)),
               said=said[:250])
    if wav: tr.save_wav(wav)
    return rec

async def main():
    blocks = int(sys.argv[1]) if len(sys.argv)>1 else 6
    seed = int(sys.argv[2]) if len(sys.argv)>2 else 20260918
    cells=[(m,lv,mode,d) for m,lv in (("gemini-3.8-live",None),
                                      ("gemini-3.8-live-extended-thinking","HIGH"))
           for mode in ("blocking","nb_silent","nb_progress") for d in (3.0,6.0,15.0)]
    rnd=random.Random(seed); rows=[]
    print("条件%d x %dブロック = %d試行 / seed=%d / sdk=%s" % (len(cells),blocks,len(cells)*blocks,seed,rig.SDK))
    for b in range(blocks):
        order=cells[:]; rnd.shuffle(order)
        for i,(m,lv,mode,d) in enumerate(order):
            wav="%s/out/tools/%s_%s_%.0fs_b%d.wav"%(HERE, "ET" if lv else "38", mode, d, b)
            r=await trial(m,mode,d,lv,wav,use_scheduling=(lv is None))
            r.update(block_index=b, trial_index=i, seed=seed); rows.append(r)
            print("  b%d %-4s %-11s %4.0fs %s 無音%6s ツール内無音%7s 実行中発話%6s 回答%s%s"
                  % (b, "ET" if lv else "3.8", mode, d,
                     "ok " if r["ok"] else ("ERR" if r["err"] else "--"),
                     r.get("max_silence_ms"), r.get("tool_gap_ms"),
                     r.get("play_in_tool_ms"), "○" if r.get("answer_ok") else "×",
                     " 漏洩" if r.get("leaked") else ""))
            await asyncio.sleep(0.5)
    fn="%s/data/e17_tools.csv"%HERE
    keys=sorted({k for r in rows for k in r})
    with open(fn,"w",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=keys); w.writeheader(); w.writerows(rows)
    print("saved:",fn,"rows:",len(rows))

if __name__=="__main__": asyncio.run(main())

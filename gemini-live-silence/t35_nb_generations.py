"""NON_BLOCKING + will_continue は 3.8 で初めて可能になったのか。
同一コード・同一進捗スケジュールを 2.5 / 3.1 / 3.8 / 3.8-ET に流して比べる。
指標は「体感の最大無音(再生カーソル基準)」「進捗→発話の追従回数」「エラー」。"""
import asyncio, os, sys, time, contextlib, csv, json
from google.genai import types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_rt as L
HERE = os.path.dirname(os.path.abspath(__file__))

STEPS = [(1.5,"接続を確認しています"),(3.0,"メトリクスを取得中です"),(4.5,"ログを確認しています")]
SYS = ("あなたは運用担当のアシスタントです。サーバの状況を聞かれたら check_server_status を呼び、"
       "途中経過が届いたらその都度ひとこと声に出して伝えてください。返答は日本語で短く。")

def tool(behavior):
    fd = types.FunctionDeclaration(
        name="check_server_status", description="サーバの稼働状況を調べる。時間がかかる。",
        parameters=types.Schema(type="OBJECT",
            properties={"server": types.Schema(type="STRING")}, required=["server"]))
    if behavior: fd.behavior = behavior
    return types.Tool(function_declarations=[fd])

async def run(model, behavior, tag):
    c = L.client_aistudio()
    cfg = types.LiveConnectConfig(response_modalities=["AUDIO"], system_instruction=SYS,
            tools=[tool(behavior)], output_audio_transcription=types.AudioTranscriptionConfig())
    ev=[]; audio=[]; err=""
    try:
        async with c.aio.live.connect(model=model, config=cfg) as s:
            t0=time.perf_counter(); rel=lambda: round((time.perf_counter()-t0)*1000)
            done=asyncio.Event()
            async def recv():
                while True:
                    async for m in s.receive():
                        sc=m.server_content
                        if sc:
                            if sc.model_turn:
                                for p in sc.model_turn.parts:
                                    if p.inline_data and p.inline_data.data:
                                        audio.append((rel(), len(p.inline_data.data)))
                            if sc.output_transcription and sc.output_transcription.text:
                                ev.append((rel(),"say",sc.output_transcription.text))
                            if sc.interrupted: ev.append((rel(),"interrupted",""))
                            if sc.turn_complete: ev.append((rel(),"turn_complete",""))
                        if m.tool_call:
                            for fc in m.tool_call.function_calls:
                                ev.append((rel(),"tool_call",fc.name))
                                asyncio.create_task(prog(fc))
            async def prog(fc):
                prev=0
                for t,msg in STEPS:
                    await asyncio.sleep(t-prev); prev=t
                    ev.append((rel(),"progress",msg))
                    try:
                        await s.send_tool_response(function_responses=[types.FunctionResponse(
                            id=fc.id, name=fc.name, will_continue=True,
                            scheduling=types.FunctionResponseScheduling.WHEN_IDLE,
                            response={"output":msg})])
                    except Exception as e:
                        ev.append((rel(),"prog_err",str(e)[:70])); return
                await asyncio.sleep(1.5)
                ev.append((rel(),"final",""))
                with contextlib.suppress(Exception):
                    await s.send_tool_response(function_responses=[types.FunctionResponse(
                        id=fc.id, name=fc.name, will_continue=False,
                        scheduling=types.FunctionResponseScheduling.INTERRUPT,
                        response={"output":{"status":"正常","cpu":"32%","uptime":"14日"}})])
                done.set()
            r=asyncio.create_task(recv())
            await s.send_client_content(turns=types.Content(role="user",
                parts=[types.Part(text="本番サーバ web-01 の状況を確認して。")]), turn_complete=True)
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(done.wait(), timeout=13)
            await asyncio.sleep(3.5)
            r.cancel()
            with contextlib.suppress(asyncio.CancelledError): await r
    except Exception as e:
        err = "%s: %s" % (type(e).__name__, str(e)[:90])
    cur=0; worst=0
    for at,n in audio:
        worst=max(worst, at-cur); cur=max(at,cur)+n/48
    # 進捗 -> その後2.5秒以内に発話があったか
    follow=0
    says=[m for m,k,_ in ev if k=="say"]
    for m,k,_ in ev:
        if k=="proess" : pass
    for m,k,_ in ev:
        if k=="progress" and any(m < s2 <= m+2500 for s2 in says): follow+=1
    return dict(model=model, mode=tag, err=err,
                max_silence_ms=worst if audio else "",
                play_sec=round(sum(n for _,n in audio)/48/1000,2),
                n_progress=sum(1 for _,k,_ in ev if k=="progress"),
                n_follow=follow,
                n_interrupted=sum(1 for _,k,_ in ev if k=="interrupted"),
                prog_err=";".join(v for _,k,v in ev if k=="prog_err")[:80],
                said="".join(v for _,k,v in ev if k=="say")[:120])

async def main():
    rows=[]
    plan=[("gemini-3.8-live", types.Behavior.NON_BLOCKING,"NB"),
          ("gemini-3.1-flash-live-preview", types.Behavior.NON_BLOCKING,"NB"),
          ("gemini-2.5-flash-native-audio-latest", types.Behavior.NON_BLOCKING,"NB"),
          ("gemini-3.8-live", None,"既定(BLOCKING)"),
          ("gemini-3.1-flash-live-preview", None,"既定(BLOCKING)"),
          ("gemini-2.5-flash-native-audio-latest", None,"既定(BLOCKING)")]
    for m,b,tag in plan:
        r = await run(m,b,tag); rows.append(r)
        print("%-38s %-14s 無音%6s ms 再生%5.2fs 進捗%d→追従%d 割込%d %s"
              % (r["model"], r["mode"], r["max_silence_ms"], r["play_sec"],
                 r["n_progress"], r["n_follow"], r["n_interrupted"],
                 ("ERR "+r["err"]) if r["err"] else ""))
        if r["prog_err"]: print("      進捗送信エラー: %s" % r["prog_err"])
        print("      発話: %r" % r["said"][:100])
        await asyncio.sleep(1.0)
    fn="%s/data/e15_nb_generations.csv"%HERE
    with open(fn,"w",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=sorted({k for r in rows for k in r})); w.writeheader(); w.writerows(rows)
    print("saved:",fn)

if __name__=="__main__": asyncio.run(main())

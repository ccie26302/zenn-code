"""ローカル用 Gemini Live プロキシ。
APIキーはサーバ側に置き、ブラウザには出さない。
ブラウザ <-(WS: 16kHz PCM)-> このサーバ <-(Live API)-> Gemini
"""
import asyncio, json, os, sys, time, base64, contextlib
from aiohttp import web, WSMsgType
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google.genai import types
import rig

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")

TOOL_DESC = "サーバの稼働状況を調べる。結果が返るまで時間がかかる。"
RESULT = {"status": "正常", "cpu": "32%", "uptime": "14日"}

def build_cfg(p):
    fd = types.FunctionDeclaration(
        name="check_server_status", description=TOOL_DESC,
        parameters=types.Schema(type="OBJECT",
            properties={"server": types.Schema(type="STRING")}, required=["server"]))
    if p["toolMode"].startswith("nb"):
        fd.behavior = types.Behavior.NON_BLOCKING
    cfg = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=p["systemInstruction"],
        tools=[types.Tool(function_declarations=[fd])],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig())
    if p.get("thinkingLevel"):
        cfg.thinking_config = types.ThinkingConfig(thinking_level=p["thinkingLevel"])
    return cfg

async def ws_handler(request):
    ws = web.WebSocketResponse(max_msg_size=8*1024*1024)
    await ws.prepare(request)
    params = None
    # 最初のメッセージで設定を受け取る
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            params = json.loads(msg.data)
            break
    if params is None:
        return ws
    model = params["model"]
    use_sched = "extended-thinking" not in model      # ET は scheduling 非対応
    client = rig.client()
    t0 = time.perf_counter()
    rel = lambda: round((time.perf_counter()-t0)*1000)
    async def send(o):
        with contextlib.suppress(Exception):
            await ws.send_str(json.dumps(o, ensure_ascii=False))
    try:
        async with client.aio.live.connect(model=model, config=build_cfg(params)) as sess:
            await send({"t":"ready","ms":rel(),"model":model,"toolMode":params["toolMode"]})

            async def on_tool(fc):
                delay = float(params.get("toolDelay", 6.0))
                await send({"t":"tool_call","ms":rel(),"name":fc.name,"args":dict(fc.args or {})})
                if params["toolMode"] == "nb_progress":
                    step, prev = 1.5, 0.0
                    n = max(0, int(delay/step) - 0 )
                    for i in range(1, n+1):
                        tt = i*step
                        if tt >= delay: break
                        await asyncio.sleep(tt-prev); prev = tt
                        fr = types.FunctionResponse(id=fc.id, name=fc.name, will_continue=True,
                                                    response={"output":"調査中です"})
                        if use_sched: fr.scheduling = types.FunctionResponseScheduling.WHEN_IDLE
                        await send({"t":"progress","ms":rel(),"text":"調査中です"})
                        with contextlib.suppress(Exception):
                            await sess.send_tool_response(function_responses=[fr])
                    await asyncio.sleep(max(0.0, delay-prev))
                else:
                    await asyncio.sleep(delay)
                fr = types.FunctionResponse(id=fc.id, name=fc.name, response={"output":RESULT})
                if params["toolMode"].startswith("nb"):
                    fr.will_continue = False
                    if use_sched: fr.scheduling = types.FunctionResponseScheduling.INTERRUPT
                await send({"t":"tool_result","ms":rel()})
                with contextlib.suppress(Exception):
                    await sess.send_tool_response(function_responses=[fr])

            async def pump():
                while True:
                    async for m in sess.receive():
                        sc = m.server_content
                        if sc:
                            if sc.model_turn:
                                for p in sc.model_turn.parts:
                                    if p.inline_data and p.inline_data.data:
                                        await send({"t":"audio","ms":rel(),
                                                    "b64":base64.b64encode(p.inline_data.data).decode()})
                            if sc.input_transcription and sc.input_transcription.text:
                                await send({"t":"heard","ms":rel(),"text":sc.input_transcription.text})
                            if sc.output_transcription and sc.output_transcription.text:
                                await send({"t":"say","ms":rel(),"text":sc.output_transcription.text})
                            if sc.interrupted: await send({"t":"interrupted","ms":rel()})
                            if sc.turn_complete: await send({"t":"turn_complete","ms":rel()})
                        if m.tool_call:
                            for fc in m.tool_call.function_calls:
                                asyncio.create_task(on_tool(fc))

            task = asyncio.create_task(pump())
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    await sess.send_realtime_input(
                        audio=types.Blob(data=msg.data, mime_type="audio/pcm;rate=16000"))
                elif msg.type == WSMsgType.TEXT:
                    o = json.loads(msg.data)
                    if o.get("t") == "text":
                        await sess.send_client_content(
                            turns=types.Content(role="user", parts=[types.Part(text=o["text"])]),
                            turn_complete=True)
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                    break
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError): await task
    except Exception as e:
        await send({"t":"error","ms":rel(),"text":"%s: %s" % (type(e).__name__, str(e)[:200])})
    with contextlib.suppress(Exception): await ws.close()
    return ws

NOCACHE = {"Cache-Control": "no-store, must-revalidate", "Pragma": "no-cache"}

async def index(request):
    return web.FileResponse(os.path.join(STATIC, "index.html"), headers=NOCACHE)

async def static_nocache(request):
    name = request.match_info["name"]
    path = os.path.join(STATIC, name)
    if not os.path.isfile(path): raise web.HTTPNotFound()
    return web.FileResponse(path, headers=NOCACHE)

app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/ws", ws_handler)
app.router.add_get("/static/{name}", static_nocache)

if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=8777)

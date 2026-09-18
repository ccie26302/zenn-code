let ws=null, micCtx=null, micNode=null, micStream=null, outCtx=null;
let playCursor=0, t0=0, maxSil=0, ttfa=null, playTotal=0, silTimer=null;
// 「応答を待っている区間」だけを無音として数える
let pendingSince=null, pendingWhy='', loggedThisEpisode=false;
const $=id=>document.getElementById(id);
const log=(k,ms,txt)=>{const d=document.createElement('div');d.className='l';
  d.innerHTML=`<i>${ms==null?'':ms+'ms'}</i><span class="k-${k}">${k}</span><span>${txt??''}</span>`;
  const L=$('log'); L.appendChild(d);
  while(L.childNodes.length>400) L.removeChild(L.firstChild);
  L.scrollTop=1e9;};

function resetStats(){playCursor=0;maxSil=0;ttfa=null;playTotal=0;
  pendingSince=null;pendingWhy='';loggedThisEpisode=false;
  $('sNow').textContent='–';$('sMax').textContent='–';$('sTtfa').textContent='–';$('sPlay').textContent='–';}
function beginWait(why){ if(pendingSince===null){pendingSince=performance.now();pendingWhy=why;loggedThisEpisode=false;} }
function endWait(){
  if(pendingSince!==null){
    const d=performance.now()-pendingSince;
    if(d>maxSil){maxSil=d;$('sMax').textContent=Math.round(maxSil);}
    pendingSince=null;$('sNow').textContent='0';
  }
}

function tickSilence(){
  // 音が鳴っている間は待ちを終える
  if(outCtx && playCursor>outCtx.currentTime) endWait();
  if(pendingSince===null){$('meterBar').style.width='100%';
    $('meterBar').style.background='#81c995';return;}
  const d=performance.now()-pendingSince;
  $('sNow').textContent=Math.round(d);
  $('meterBar').style.width=Math.max(0,100-Math.min(100,d/80))+'%';
  $('meterBar').style.background = d>2000 ? '#f28b82' : (d>800?'#fdd663':'#81c995');
  if(d>maxSil){maxSil=d;$('sMax').textContent=Math.round(maxSil);}
  // 1つの待ち区間につき1回だけ記録する
  if(d>2000 && !loggedThisEpisode){loggedThisEpisode=true;
    log('silence',null,`${pendingWhy} から 2秒を超えて無音`);}
}

async function start(){
  resetStats(); $('log').innerHTML='';
  outCtx=new AudioContext({sampleRate:24000});
  await outCtx.resume(); playCursor=outCtx.currentTime;
  micStream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,
     echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
  micCtx=new AudioContext({sampleRate:16000});
  await micCtx.audioWorklet.addModule('/static/capture.js');
  const src=micCtx.createMediaStreamSource(micStream);
  micNode=new AudioWorkletNode(micCtx,'capture');
  src.connect(micNode);
  ws=new WebSocket(`ws://${location.host}/ws`);
  ws.binaryType='arraybuffer';
  ws.onopen=()=>{ws.send(JSON.stringify({
      model:$('model').value, thinkingLevel:($('model').value.includes('extended')?$('think').value:''),
      toolMode:$('toolMode').value, toolDelay:Number($('delay').value),
      systemInstruction:"あなたは運用担当のアシスタントです。サーバの状況を聞かれたら check_server_status を呼び、途中経過が届いたらその都度ひとこと声に出して伝えてください。最終結果が届いたら状態・CPU使用率・稼働日数を読み上げてください。日本語で簡潔に。"}));
    t0=performance.now();
    micNode.port.onmessage=e=>{if(ws&&ws.readyState===1) ws.send(e.data);};
    silTimer=setInterval(tickSilence,60);
    $('start').disabled=true;$('stop').disabled=false;};
  ws.onmessage=ev=>{
    const m=JSON.parse(ev.data);
    if(m.t==='audio'){
      const raw=atob(m.b64); const buf=new Int16Array(raw.length/2);
      for(let i=0;i<buf.length;i++) buf[i]=(raw.charCodeAt(i*2)|(raw.charCodeAt(i*2+1)<<8))<<16>>16;
      const f=new Float32Array(buf.length); for(let i=0;i<buf.length;i++) f[i]=buf[i]/32768;
      const ab=outCtx.createBuffer(1,f.length,24000); ab.getChannelData(0).set(f);
      const s=outCtx.createBufferSource(); s.buffer=ab; s.connect(outCtx.destination);
      const at=Math.max(outCtx.currentTime,playCursor); s.start(at);
      playCursor=at+ab.duration; lastEnd=playCursor; playTotal+=ab.duration;
      $('sPlay').textContent=playTotal.toFixed(2);
      if(ttfa===null){ttfa=m.ms;$('sTtfa').textContent=ttfa;}
      endWait();
      return;
    }
    if(m.t==='heard'){ log(m.t,m.ms,m.text); beginWait('こちらの発話'); }
    else if(m.t==='say') log(m.t,m.ms,m.text);
    else if(m.t==='tool_call'){ log(m.t,m.ms,`${m.name}(${JSON.stringify(m.args)}) → ${$('delay').value}秒かかる想定`); beginWait('ツール呼び出し'); }
    else if(m.t==='progress') log(m.t,m.ms,'進捗を返した: '+m.text);
    else if(m.t==='tool_result'){ log(m.t,m.ms,'最終結果を返した'); beginWait('最終結果の送信'); }
    else if(m.t==='ready') log(m.t,m.ms,`${m.model} / ${m.toolMode}`);
    else if(m.t==='error') log(m.t,m.ms,m.text);
    else log(m.t,m.ms,'');
  };
  ws.onclose=()=>stop(true);
}
function stop(fromWs){
  if(silTimer){clearInterval(silTimer);silTimer=null;}
  if(micNode){micNode.disconnect();micNode=null;}
  if(micStream){micStream.getTracks().forEach(t=>t.stop());micStream=null;}
  if(micCtx){micCtx.close();micCtx=null;}
  if(ws&&!fromWs){ws.close();} ws=null;
  $('start').disabled=false;$('stop').disabled=true;
}
$('start').onclick=()=>start().catch(e=>log('error',null,e.message));
$('stop').onclick=()=>stop();
$('send').onclick=()=>{const v=$('txt').value.trim();
  if(v&&ws&&ws.readyState===1){ws.send(JSON.stringify({t:'text',text:v}));log('heard',null,'(テキスト) '+v);}};
$('txt').addEventListener('keydown',e=>{if(e.key==='Enter')$('send').click();});

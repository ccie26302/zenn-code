class Capture extends AudioWorkletProcessor{
  constructor(){super();this.buf=[];this.need=320;}   // 20ms @16kHz
  process(inputs){
    const ch=inputs[0][0]; if(!ch) return true;
    for(let i=0;i<ch.length;i++) this.buf.push(ch[i]);
    while(this.buf.length>=this.need){
      const s=this.buf.splice(0,this.need);
      const pcm=new Int16Array(this.need);
      for(let i=0;i<this.need;i++){const v=Math.max(-1,Math.min(1,s[i]));pcm[i]=v*32767;}
      this.port.postMessage(pcm.buffer,[pcm.buffer]);
    }
    return true;
  }
}
registerProcessor('capture',Capture);

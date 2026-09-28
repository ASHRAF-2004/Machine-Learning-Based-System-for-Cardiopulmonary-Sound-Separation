// Device PCM acquisition only. Source separation always runs in the worker.
class PcmCapture extends AudioWorkletProcessor {
  constructor() {
    super(); this.active = true; this.buffer = new Float32Array(2048); this.used = 0;
    this.port.onmessage = ({data}) => {
      if (data === 'stop') { this.active = false; this.flush(); this.port.postMessage({stopped:true}); }
    };
  }
  flush() {
    if (this.used) { const chunk = this.buffer.slice(0,this.used); this.port.postMessage({samples:chunk},[chunk.buffer]); this.used = 0; }
  }
  process(inputs) {
    const channels = inputs[0];
    if (!this.active) return false;
    if (channels?.length) for (let i=0;i<channels[0].length;i++) {
      let sample=0; for(const channel of channels) sample+=channel[i]/channels.length;
      this.buffer[this.used++]=sample;
      if(this.used===this.buffer.length)this.flush();
    }
    return true;
  }
}
registerProcessor('stethofuse-pcm-capture',PcmCapture);

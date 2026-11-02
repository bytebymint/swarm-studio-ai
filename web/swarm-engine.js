/* SWARM STUDIO: independently implemented scheduling, motion and rendering. */
(() => {
  'use strict';
  const clamp = (value,lo,hi) => Math.max(lo,Math.min(hi,value));
  const ease = t => t*t*(3-2*t);
  class EventSound {
    constructor(settings) {this.settings=settings;this.last=0;}
    play(kind,x=.5) {
      if (!this.settings.sound || this.settings.reduced_audio && kind==='type') return;
      if(this.ledger){const now=this.captureTime||0;if(now-this.last<.035)return;this.last=now;this.ledger.push({time:now,kind,x,volume:this.settings.volume??.25});return;}
      try {
        this.ctx ||= new AudioContext();
        if(this.ctx.state==='suspended') this.ctx.resume().catch(()=>{});
        const ctx=this.ctx, now=ctx.currentTime;
        if(now-this.last<.035) return; this.last=now;
        const gain=ctx.createGain(), pan=ctx.createStereoPanner();
        pan.pan.value=clamp(x*2-1,-1,1);gain.connect(pan).connect(ctx.destination);
        const volume=clamp(this.settings.volume??.25,0,1);
        gain.gain.setValueAtTime(volume*.08,now);gain.gain.exponentialRampToValueAtTime(.0001,now+(kind==='complete'?.8:.09));
        if(kind==='type'||kind==='click') {
          const buffer=ctx.createBuffer(1,Math.ceil(ctx.sampleRate*.025),ctx.sampleRate), data=buffer.getChannelData(0);
          for(let i=0;i<data.length;i++) data[i]=(Math.random()*2-1)*Math.exp(-i/180);
          const source=ctx.createBufferSource();source.buffer=buffer;source.connect(gain);source.start();
          const osc=ctx.createOscillator();osc.frequency.setValueAtTime(kind==='type'?190:420,now);osc.connect(gain);osc.start();osc.stop(now+.035);
        } else {
          const notes=kind==='complete'?[164.81,207.65,246.94,329.63]:[164.81,185,207.65,246.94,277.18];
          const tones=kind==='complete'?notes:[notes[Math.floor(clamp(x,0,.999)*notes.length)]*2];
          for(const hz of tones){const osc=ctx.createOscillator();osc.type='sine';osc.frequency.value=hz;osc.connect(gain);osc.start();osc.stop(now+(kind==='complete'?.9:.2));}
        }
      } catch (_) { /* Audio must never block playback. */ }
    }
    
  }

})();

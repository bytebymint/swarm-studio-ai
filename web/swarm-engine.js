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
    close(){this.ctx?.close().catch(()=>{});}
  }

  class StudioEngine {
    constructor(){
      this.frame=document.querySelector('#site');this.canvas=document.querySelector('#overlay');this.ctx=this.canvas.getContext('2d');
      this.intro=document.querySelector('#intro');this.completion=document.querySelector('#completion');this.running=false;this.paused=false;
      this.last=performance.now();this.mouse={x:innerWidth/2,y:innerHeight/2};this.lastReport=0;this.settings={};
      addEventListener('resize',()=>this.resize());this.resize();
      addEventListener('mousemove',event=>{this.mouse={x:event.clientX,y:event.clientY};});
      document.querySelector('#explore').onclick=()=>{this.showClone();this.emit('explore',{});};
      document.querySelector('#compare').onclick=()=>this.emit('compare',{});
      document.querySelector('#replay').onclick=()=>this.replay();
      document.addEventListener('keydown',event=>{if(event.code==='Space'&&event.target===document.body){event.preventDefault();this.pause(!this.paused);}if(event.key==='Escape')this.pause(true);});
      requestAnimationFrame(time=>this.loop(time));
    }
    get width(){return this.presentation?.enabled?this.presentation.logicalWidth:innerWidth;}
    get height(){return this.presentation?.enabled?this.presentation.logicalHeight:innerHeight;}
    resize(){const dpr=devicePixelRatio||1;this.canvas.width=innerWidth*dpr;this.canvas.height=innerHeight*dpr;this.ctx.setTransform(dpr,0,0,dpr,0,0);}
    random(){this.seed^=this.seed<<13;this.seed^=this.seed>>>17;this.seed^=this.seed<<5;return(this.seed>>>0)/4294967296;}

  }

})();

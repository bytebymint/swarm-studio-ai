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
    emit(type,data){const event={type,...data};this.events?.push(event);if(this.events?.length>100)this.events.shift();if(!this.seeking)window.studioBridge?.publish(JSON.stringify(event));}
    async load(project,settings={}){
      this.settings=settings;this.project=project;this.running=false;this.sound?.close();this.sound=new EventSound(settings);
      const response=await fetch(project+'metadata/blueprint.json');if(!response.ok)throw new Error('Blueprint could not be loaded.');
      this.model=await response.json();
      await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(new Error('Local clone did not load within 15 seconds.')),15000);this.frame.onload=()=>{clearTimeout(timeout);resolve();};this.frame.src=project+'index.html';});
      await Promise.race([this.frame.contentDocument.fonts.ready,new Promise(r=>setTimeout(r,1200))]);
      this.frameListeners?.abort();this.frameListeners=new AbortController();
      this.frame.contentDocument.addEventListener('mousemove',event=>{this.mouse={x:event.clientX,y:event.clientY};},{signal:this.frameListeners.signal});
      this.frame.contentDocument.addEventListener('pointerdown',()=>this.sound.ctx?.resume().catch(()=>{}),{signal:this.frameListeners.signal});
      this.frame.contentDocument.addEventListener('wheel',()=>this.camera?.interrupt(),{passive:true,signal:this.frameListeners.signal});
      this.prepare();this.emit('ready',{total:this.tasks.length});
    }
    prepare(){
      this.restore();
      this.seed=112358;this.time=0;this.done=0;this.failed=0;this.finished=false;this.paused=false;this.events=[];this.history=[];
      this.doc=this.frame.contentDocument;
      this.oldMask?.remove();
      this.oldMask=this.doc.createElement('style');this.oldMask.textContent='html,[data-sw-id]{scroll-behavior:auto!important;overflow-anchor:none!important}[data-sw-id][data-sw-state="pending"]{visibility:hidden!important}[data-sw-id][data-sw-state="active"]{visibility:visible!important}::highlight(swarm-untyped){color:transparent;text-shadow:none}';this.doc.head.append(this.oldMask);
      this.textOriginal ||= new Map();
      for(const [node,text] of this.textOriginal)if(node.isConnected)node.textContent=text;
      this.textOriginal.clear();
      this.elements=new Map(this.model.elements.map(e=>[e.id,{...e,node:this.doc.querySelector(`[data-sw-id="${e.id}"]`)}]));
      for(const e of this.elements.values()){
        if(!e.node)continue;
        e.savedClip={value:e.node.style.getPropertyValue('clip-path'),priority:e.node.style.getPropertyPriority('clip-path')};
        e.node.setAttribute('data-sw-state','pending');
        e.textNodes=[];for(const node of e.node.childNodes)if(node.nodeType===3&&node.textContent.trim()){e.textNodes.push([node,node.textContent]);this.textOriginal.set(node,node.textContent);}
      }
      this.tasks=this.model.tasks.map(t=>({...t,status:'pending',elapsed:0,scaffolded:false}));this.byId=new Map(this.tasks.map(t=>[t.id,t]));
      this.boundsCache=new Map();
      this.choreography=new TaskChoreography(this);
      this.crew=new WorkingCrew(this);this.agents=this.crew.members;
      this.scrollContainers=[this.doc.scrollingElement,...this.doc.querySelectorAll('[data-sw-id]')].filter(n=>n&&n.scrollHeight>n.clientHeight+30&&(/auto|scroll/.test(this.frame.contentWindow.getComputedStyle(n).overflowY)||n===this.doc.scrollingElement));
      for(const node of this.scrollContainers)node.scrollTop=0;
      this.frame.contentWindow.scrollTo(0,0);this.intro.hidden=false;this.intro.style.display='flex';this.intro.style.opacity='1';this.completion.hidden=true;this.canvas.style.display='block';
      this.canvas.style.opacity=this.settings.overlay_opacity??1;this.running=true;this.introDuration=(this.settings.intro===false||this.settings.reduced_motion) ? .15 : 1.1;
      this.camera=new CinematicTour(this);
      if(!this.tasks.length)this.finish();
    }
    box(element){if(this.boundsCache?.has(element.id))return this.boundsCache.get(element.id);const rect=element.node?.getBoundingClientRect();const box=rect?{x:rect.x,y:rect.y,w:rect.width,h:rect.height}:element.rect;this.boundsCache?.set(element.id,box);return box;}
    isVisible(e){if(!e.node)return false;const r=this.box(e);if(r.y+r.h<0||r.y>this.height||r.x+r.w<0||r.x>this.width)return false;let parent=e.node.parentElement;while(parent&&parent!==this.doc.body){const cs=this.frame.contentWindow.getComputedStyle(parent);if(/auto|scroll|hidden|clip/.test(cs.overflowY)){const p=parent.getBoundingClientRect();if(r.y>p.bottom||r.y+r.h<p.top)return false;}parent=parent.parentElement;}return true;}
    dependencyPhase(task,id){
      if(task.dependencyPhases?.[id])return task.dependencyPhases[id];
      const element=this.elements.get(task.element),parent=this.elements.get(id);
      return id===element?.parent&&id!==element?.master&&parent?.kind==='container'?'frame':'complete';
    }
    ready(task){return task.status==='pending'&&task.dependencies.every(id=>{const dep=this.byId.get(id);return dep?.status==='complete'||this.dependencyPhase(task,id)==='frame'&&dep?.scaffolded;});}
    assign(agent,task){this.choreography.begin(agent,task);}
    tour(dt){
      this.camera.update(dt);
    }
    tick(dt){
      this.time+=dt;
      this.boundsCache?.clear();
      const introP=clamp(this.time/this.introDuration,0,1);this.intro.style.opacity=String(1-ease(clamp((introP-.55)/.45,0,1)));
      if(introP>=1)this.intro.style.display='none';
      if(introP>=1&&!this.finished){
        // Explicit failure propagation prevents a stalled graph from claiming success.
        for(const task of this.tasks){if(task.status==='pending'&&(!this.elements.get(task.element)?.node||this.elements.get(task.element)?.validation==='failed'||task.dependencies.some(id=>['failed','blocked'].includes(this.byId.get(id)?.status)))){task.status='blocked';this.failed++;this.emit('task-error',{task:task.id,label:task.label});}}
        this.tour(dt);
        this.boundsCache.clear();
        this.crew.dispatch();
        for(const agent of this.agents)if(agent.task)this.choreography.update(agent,this.director?this.director.taskDelta(agent,dt):dt);
        if(this.done+this.failed===this.tasks.length&&!this.agents.some(a=>a.task))this.finish();
      }
      this.crew.animate(dt);
    }
    finish(){this.finished=true;this.finishTime=this.time;this.completion.hidden=false;document.querySelector('#completion-detail').textContent=`${this.done} built${this.failed?' · '+this.failed+' failed':''}`;this.sound.play('complete');this.emit('finished',{completed:this.done,failed:this.failed,total:this.tasks.length});}
    draw(){
      const ctx=this.ctx;ctx.clearRect(0,0,innerWidth,innerHeight);ctx.lineWidth=1;
      ctx.save();
      if(this.presentation?.enabled){const m=this.presentation.apply();ctx.translate(m.x,m.y);ctx.scale(m.scale,m.scale);ctx.beginPath();ctx.rect(0,0,this.width,this.height);ctx.clip();}
      this.choreography?.render(ctx);
      this.crew?.render(ctx);
      ctx.restore();
    }
    report(){if(!this.model)return;this.emit('progress',{time:this.time||0,completed:this.done||0,failed:this.failed||0,total:this.tasks?.length||0,paused:this.paused,finished:this.finished,agents:this.agents?.map(a=>({id:a.id,status:a.phase,completed:a.completed,task:a.task?.id||null}))||[]});}
    loop(now){const realDt=Math.min((now-this.last)/1000,.05);this.last=now;if(this.running&&!this.paused&&!this.externalClock){const duration=realDt*(this.settings.speed||1);const steps=Math.max(1,Math.ceil(duration/.016));for(let i=0;i<steps;i++)this.tick(duration/steps);this.director?.update(realDt);this.draw();}if(this.running&&!this.externalClock&&now-this.lastReport>180){this.lastReport=now;this.report();}requestAnimationFrame(t=>this.loop(t));}
    startCapture(options={}){
      this.presentation??=new MoviePresentation(this);
      this.presentation.enable(options.width||innerWidth,options.height||innerHeight);
      this.settings.auto_tour=true;this.externalClock=true;this.prepare();this.paused=true;
      this.director=new RecordingDirector(this,options.zoom||3);
      this.sound.ledger=[];this.sound.last=-100;this.captureIndex=0;
      this.freezeStyle?.remove();this.freezeStyle=this.doc.createElement('style');
      this.freezeStyle.textContent='*,*::before,*::after{transition:none!important;animation-play-state:paused!important;caret-color:transparent!important}';this.doc.head.append(this.freezeStyle);
      for(const animation of this.doc.getAnimations()){try{animation.pause();animation.currentTime=animation.effect.getTiming().iterations===Infinity?0:animation.effect.getComputedTiming().endTime;}catch(_){}}
      this.draw();return true;
    }
    advanceCaptureFrame(index,fps=60,speed=1,render=true){
      if(index!==this.captureIndex)throw new Error('Capture frames must be sequential');
      const steps=Math.max(1,Math.ceil(speed/fps*60)),dt=speed/fps/steps;
      for(let i=0;i<steps;i++){this.sound.captureTime=(index+i/steps)/fps;this.tick(dt);}
      this.director.update(1/fps);this.captureIndex++;if(render)this.draw();
      return {finished:this.director.finished,completed:this.done,total:this.tasks.length,time:this.time,pose:{...this.director.pose},state:this.director.state};
    }
    endCapture(){this.externalClock=false;this.director=null;this.presentation?.disable();this.freezeStyle?.remove();this.sound.ledger=null;this.prepare();this.draw();}
    pause(value=true){this.paused=value;this.report();}
    setSpeed(speed){this.settings.speed=clamp(Number(speed)||1,.5,5);}
    setOptions(options){Object.assign(this.settings,options);}
    step(){this.paused=true;for(let i=0;i<30;i++)this.tick(1/60);this.draw();this.report();}
    back(){const target=Math.max(0,this.time-2);this.seeking=true;this.prepare();for(let i=0;i<Math.floor(target*60);i++)this.tick(1/60);this.seeking=false;this.paused=true;this.draw();this.report();}
    replay(){if(this.frame.contentWindow.location.href!==this.project+'index.html'){this.load(this.project,this.settings).catch(error=>this.emit('error',{message:error.message}));return;}this.prepare();this.emit('replayed',{});}
    stop(){this.running=false;this.sound?.close();this.ctx.clearRect(0,0,innerWidth,innerHeight);this.restore();this.intro.style.display='none';this.completion.hidden=true;this.emit('cancelled',{});}
    restoreClip(e){if(!e.node)return;if(e.savedClip?.value)e.node.style.setProperty('clip-path',e.savedClip.value,e.savedClip.priority);else e.node.style.removeProperty('clip-path');}
    restore(){this.choreography?.dispose();this.oldMask?.remove();for(const e of this.elements?.values()||[]){e.node?.removeAttribute('data-sw-state');this.restoreClip(e);for(const [node,text] of e.textNodes||[])node.textContent=text;}}
    showClone(){this.running=false;this.restore();this.boundsCache?.clear();this.canvas.style.display='none';this.intro.style.display='none';this.completion.hidden=true;const state=this.model?.scrollState;if(state){for(const[id,position]of Object.entries(state.nodes||{})){const node=this.frame.contentDocument.querySelector(`[data-sw-id="${id}"]`);if(node)node.scrollTo({top:position.top,left:position.left,behavior:'instant'});}if(state.window)this.frame.contentWindow.scrollTo({left:state.window.x,top:state.window.y,behavior:'instant'});}}
  }
  window.Studio=new StudioEngine();
  if(typeof QWebChannel!=='undefined'&&window.qt?.webChannelTransport)new QWebChannel(qt.webChannelTransport,channel=>{window.studioBridge=channel.objects.bridge;window.Studio.emit('bridge-ready',{});});
  
})();

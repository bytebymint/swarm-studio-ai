/* Saved local media only. No source scripts, remote sessions or wall-clock movie playback. */
(() => {
  class StudioMedia {
    constructor(engine){this.engine=engine;this.items=[];this.warnings=engine.mediaWarnings||[];engine.mediaWarnings=this.warnings;this.listeners=new AbortController();
      for(const e of engine.elements.values())if(e.media?.status==='downloaded'&&e.node?.tagName==='VIDEO'){
        const v=e.node;v.autoplay=false;v.muted=true;v.pause();v.preload='auto';v.playbackRate=Math.max(.1,e.media.playbackRate||1);
        this.items.push({e,v,started:false,failed:false,base:Math.max(0,e.media.currentTime||0)});
        const restorePosition=()=>{if(!engine.externalClock&&Number.isFinite(v.duration))v.currentTime=Math.min(e.media.currentTime||0,Math.max(0,v.duration-.001));};
        if(v.readyState>=1)restorePosition();else v.addEventListener('loadedmetadata',restorePosition,{once:true,signal:this.listeners.signal});
        v.addEventListener('error',()=>this.fail(this.items.find(i=>i.v===v),'Browser cannot decode this saved video'),{once:true,signal:this.listeners.signal});
      }
    }
    fail(item,reason){if(!item||item.failed)return;item.failed=true;item.v.pause();
      const fallback=this.engine.doc.createElement('div');
      for(const a of item.v.attributes)if(!['src','poster','autoplay','controls','loop','muted','preload'].includes(a.name))fallback.setAttribute(a.name,a.value);
      const box=item.v.getBoundingClientRect();fallback.style.width=box.width+'px';fallback.style.height=box.height+'px';fallback.style.maxWidth='100%';fallback.style.overflow='hidden';
      fallback.setAttribute('role','img');fallback.setAttribute('aria-label','Video unavailable: '+reason);
      if(item.v.poster){const img=this.engine.doc.createElement('img');img.src=item.v.poster;img.alt='Video poster only';img.style.cssText='width:100%;height:100%;object-fit:contain';fallback.append(img);}
      else fallback.textContent='Video unavailable: '+reason;
      item.v.replaceWith(fallback);item.e.node=fallback;this.engine.boundsCache?.clear();
      this.warnings.push({element:item.e.id,reason});this.engine.emit('media-warning',{element:item.e.id,message:reason});}
    dispose(){this.pause();this.listeners.abort();}
    reveal(element){const item=this.items.find(i=>i.e.id===element.id);if(!item||item.started)return;item.started=true;
      if(!this.engine.externalClock&&(element.media.autoplay||!element.media.paused))item.v.play().catch(()=>{});
    }
    pause(){for(const i of this.items)i.v.pause();}
    resume(){for(const i of this.items){i.v.muted=!!i.e.media.muted;if(i.started&&!i.failed&&(i.e.media.autoplay||!i.e.media.paused))i.v.play().catch(()=>{});}}
    async sync(seconds){
      // Browser decoders own bounded buffers; never retain a movie-length frame cache.
      const visible=this.items.filter(i=>!i.failed&&i.started&&this.engine.isVisible(i.e));
      const deadline=performance.now()+5000;
      for(let offset=0;offset<visible.length;offset+=4){
      if(performance.now()>=deadline){for(const item of visible.slice(offset))this.fail(item,'Video synchronization budget exceeded');break;}
      await Promise.all(visible.slice(offset,offset+4).map(async item=>{
        const {v,e}=item;v.muted=true;v.pause();
        try {
          if(v.readyState<1)await new Promise((resolve,reject)=>{
            const cleanup=()=>{clearTimeout(timer);v.removeEventListener('loadedmetadata',ok);v.removeEventListener('error',bad);};
            const ok=()=>{cleanup();resolve();},bad=()=>{cleanup();reject(new Error('Video metadata unavailable'));};
            const timer=setTimeout(bad,Math.max(1,Math.min(4000,deadline-performance.now())));v.addEventListener('loadedmetadata',ok,{once:true});v.addEventListener('error',bad,{once:true});v.load();
          });
          if(!Number.isFinite(v.duration)||v.duration<=0)throw new Error('Unsupported video duration');
          const advancing=e.media.autoplay||!e.media.paused;
          let time=item.base+(advancing?seconds*Math.max(.1,e.media.playbackRate||1):0);
          time=e.media.loop?time%v.duration:Math.min(time,Math.max(0,v.duration-.001));
          if(Math.abs(v.currentTime-time)<.00001&&v.readyState>=2)return;
          await new Promise((resolve,reject)=>{
            let callback=null;
            const cleanup=()=>{clearTimeout(timer);v.removeEventListener('seeked',seeked);v.removeEventListener('error',bad);if(callback!==null)v.cancelVideoFrameCallback?.(callback);};
            const done=()=>{cleanup();resolve();},bad=()=>{cleanup();reject(new Error('Video frame seek/decode timed out'));};
            const seeked=()=>{if(!v.requestVideoFrameCallback)done();};
            const timer=setTimeout(bad,Math.max(1,Math.min(4000,deadline-performance.now())));v.addEventListener('seeked',seeked,{once:true});v.addEventListener('error',bad,{once:true});
            if(v.requestVideoFrameCallback)callback=v.requestVideoFrameCallback(done);
            v.currentTime=time;
          });
        } catch(error){this.fail(item,error.message);}
      }));
      }
      return {warnings:this.warnings,frames:this.items.filter(i=>!i.failed).map(i=>({element:i.e.id,time:i.v.currentTime}))};
    }
  }
  window.StudioMedia=StudioMedia;
})();

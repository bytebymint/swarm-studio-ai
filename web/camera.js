/* Task-driven camera for document pages and nested scrollable app shells. */
(() => {
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const smooth = t => t*t*t*(t*(t*6-15)+10);

  class CinematicTour {
    constructor(engine) {
      this.engine = engine;
      this.doc = engine.doc;
      this.move = null;
      this.holdUntil = engine.introDuration;
      this.manualUntil = 0;
      this.atEnd = false;
      this.shots = 0;
      this.lastProgress = engine.time;
      const root = this.doc.scrollingElement;
      const hosts = engine.scrollContainers.filter(node => this.maximum(node) > 2);
      this.primary = this.maximum(root) > 2 ? root : hosts.sort((a,b) => b.clientWidth*b.clientHeight-a.clientWidth*a.clientHeight)[0];
    }
    maximum(node) { return node ? Math.max(0,node.scrollHeight-node.clientHeight) : 0; }
    port(node) {
      if (node === this.doc.scrollingElement) return {top:0,bottom:this.engine.height,height:this.engine.height};
      const rect = node.getBoundingClientRect();
      return {top:rect.top+node.clientTop,bottom:rect.top+node.clientTop+node.clientHeight,height:node.clientHeight};
    }
    interrupt() {
      this.move = null;
      this.manualUntil = this.engine.time + 1.5;
      this.atEnd = false;
    }
    start(node, target, final = false) {
      const from = node.scrollTop;
      const to = clamp(target,0,this.maximum(node));
      if (Math.abs(to-from) < 2) return false;
      if(this.engine.director&&!this.engine.director.allowScroll())return false;
      const height = Math.max(200,this.port(node).height);
      this.move = {node,from,to,elapsed:0,duration:clamp(.6+Math.abs(to-from)/(height*.62),.85,4),final};
      this.atEnd = false;
      this.shots++;
      this.engine.emit('camera-shot',{shot:this.shots,from,to,scroller:node.getAttribute('data-sw-id')||'document'});
      return true;
    }
    route(element) {
      const chain = [];
      for(let node=element.node.parentElement;node;node=node.parentElement) {
        if(this.engine.scrollContainers.includes(node)&&this.maximum(node)>2) chain.push(node);
      }
      if(!chain.includes(this.doc.scrollingElement)&&this.maximum(this.doc.scrollingElement)>2)chain.push(this.doc.scrollingElement);
      chain.reverse();
      // Reveal an inner scrolling viewport in its outer parent before moving
      // the inner content. Deep child geometry must not scroll the wrong host.
      for(let i=0;i<chain.length;i++) {
        const host=chain[i],port=this.port(host);
        const rect=(chain[i+1]||element.node).getBoundingClientRect();
        const focus=port.top+port.height*.26;
        if(rect.top>port.bottom-port.height*.12||rect.bottom<port.top+port.height*.12) {
          const target=clamp(host.scrollTop+rect.top-focus,0,this.maximum(host));
          if(Math.abs(target-host.scrollTop)>2)return {node:host,target};
        }
      }
      return null;
    }
    update(dt) {
      const e=this.engine;
      if(!e.settings.auto_tour||e.time<e.introDuration||e.finished||e.time<this.manualUntil)return;
      if(this.move) {
        const shot=this.move;
        shot.elapsed+=dt;
        const p=clamp(shot.elapsed/shot.duration,0,1);
        shot.node.scrollTop=shot.from+(shot.to-shot.from)*smooth(p);
        if(p>=1) {
          shot.node.scrollTop=shot.to;
          this.move=null;
          this.holdUntil=e.time+.45;
          if(shot.final)this.atEnd=true;
        }
        return;
      }
      if(e.time<this.holdUntil)return;
      const visual=e.tasks.filter(task=>task.operation!=='verify'&&['pending','active'].includes(task.status));
      if(!visual.length) {
        if(this.primary&&Math.abs(this.primary.scrollTop-this.maximum(this.primary))>=2){this.start(this.primary,this.maximum(this.primary),true);return;}
        this.atEnd=true;
        return;
      }
      // A final verification task often targets the always-visible body. It is
      // deliberately excluded from scene pacing, as are blocked descendants.
      const local=visual.some(task=>(task.status==='active'||e.ready(task))&&e.isVisible(e.elements.get(task.element)));
      if(local) { this.lastProgress=e.time; return; }
      const eligible=visual.filter(task=>e.ready(task));
      for(const task of eligible) {
        const element=e.elements.get(task.element);
        if(!element?.node)continue;
        const next=this.route(element);
        if(next&&this.start(next.node,next.target))return;
      }
    }
  }
  
})();

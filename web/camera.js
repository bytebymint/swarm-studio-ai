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

  }
  
})();

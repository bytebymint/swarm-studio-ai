/* Geometry-driven design-tool interactions. Text stays in its original layout. */
(() => {
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const ease=t=>t*t*t*(t*(t*6-15)+10);
  const phase=(p,a,b)=>clamp((p-a)/(b-a),0,1);
  const lerp=(a,b,t)=>a+(b-a)*t;
  const actions={draw:'Draw',type:'Type',place:'Place image',duplicate:'Duplicate',stroke:'Draw path',verify:'Check'};

  class TaskChoreography {
    constructor(engine) {
      this.engine=engine;this.effects=[];
      const win=engine.frame.contentWindow;
      this.highlight=win.Highlight&&win.CSS?.highlights?new win.Highlight():null;
      if(this.highlight)win.CSS.highlights.set('swarm-untyped',this.highlight);
      this.segmenter=win.Intl?.Segmenter?new win.Intl.Segmenter(undefined,{granularity:'grapheme'}):null;
    }
    dispose() {
      for(const element of this.engine.elements?.values()||[])this.clearText(element);
      this.engine.frame.contentWindow.CSS?.highlights?.delete('swarm-untyped');
      this.effects=[];
    }
    workRect(element) {
      const r=this.engine.box(element);
      let left=Math.max(0,r.x),top=Math.max(0,r.y),right=Math.min(this.engine.width,r.x+r.w),bottom=Math.min(this.engine.height,r.y+r.h);
      for(let node=element.node?.parentElement;node&&node!==this.engine.doc.body;node=node.parentElement) {
        const cs=this.engine.frame.contentWindow.getComputedStyle(node);
        if(/auto|scroll|hidden|clip/.test(cs.overflowY)){const p=node.getBoundingClientRect();top=Math.max(top,p.top);bottom=Math.min(bottom,p.bottom);}
        if(/auto|scroll|hidden|clip/.test(cs.overflowX)){const p=node.getBoundingClientRect();left=Math.max(left,p.left);right=Math.min(right,p.right);}
      }
      return {x:clamp(left,0,this.engine.width-2),y:clamp(top,0,this.engine.height-2),w:Math.max(1,right-left),h:Math.max(1,bottom-top)};
    }
    sourceRect(element) {
      const master=this.engine.elements.get(element.master);
      if(master?.node&&this.engine.isVisible(master))return this.workRect(master);
      const r=this.workRect(element);
      return {...r,x:clamp(r.x-28,0,this.engine.width-r.w),y:clamp(r.y-20,0,this.engine.height-r.h)};
    }

  }
  
})();

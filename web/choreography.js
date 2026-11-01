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
    anchor(element,task) {
      const r=task.operation==='duplicate'?this.sourceRect(element):this.workRect(element);
      return task.operation==='verify'?{x:r.x+Math.min(r.w*.5,90),y:r.y+8}:{x:r.x,y:r.y};
    }
    begin(agent,task) {
      const e=this.engine.elements.get(task.element),anchor=this.anchor(e,task),r=this.workRect(e);
      task.status='active';task.elapsed=0;task.scaffolded=false;task.owner=agent.id;
      task.travel=Math.max(.24,Math.hypot(anchor.x-agent.x,anchor.y-agent.y)/780)*agent.personality*Math.sqrt(clamp(this.engine.settings.smoothness||1,.4,2));
      const drawDistance=Math.hypot(r.w,r.h);
      task.build=Math.max(task.duration*agent.personality,
        ['draw','place','type'].includes(task.operation)?drawDistance/950/.65:0,
        task.operation==='type'?drawDistance/1100/.22:0,
        task.operation==='place'?drawDistance/1100/.28:0,
        task.operation==='stroke'?drawDistance/1000/.8:0,
        task.operation==='duplicate'?Math.hypot(r.x-anchor.x,r.y-anchor.y)/700/.44:0);
      task.build=clamp(task.build,.55,5.5);
      task.origin={x:agent.x,y:agent.y};
      task.bend=clamp(Math.hypot(anchor.x-agent.x,anchor.y-agent.y)*.075,8,48)*(agent.id%2?1:-1);
      task.pressed=false;task.paint=false;task.drawProgress=0;
      agent.task=task;agent.phase='Approaching';agent.tool='arrow';agent.focus=anchor;agent.pose={x:agent.x,y:agent.y};
      if(e.textNodes.length&&(task.operation==='type'||task.operation==='duplicate'))this.prepareText(e);
      const parent=task.dependencies.map(id=>this.engine.byId.get(id)).find(t=>t?.owner!==undefined&&(t.status==='complete'||t.scaffolded)&&this.engine.time-(t.completedAt??t.frameReadyAt??-100)<.85);
      if(parent&&parent.owner!==agent.id) {
        const partner=this.engine.agents[parent.owner];
        this.effects.push({kind:'handoff',from:parent.handoffPoint||{x:partner.x,y:partner.y},to:anchor,color:agent.color,start:this.engine.time,duration:.4});
        this.engine.emit('handoff',{from:parent.owner,to:agent.id,parent:parent.id,task:task.id});
      }
      this.engine.emit('assigned',{agent:agent.id,name:agent.name,task:task.id,operation:task.operation,label:task.label});
    }

  }
  
})();

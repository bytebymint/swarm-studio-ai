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
    prepareText(element) {
      this.clearText(element);
      const style=this.engine.frame.contentWindow.getComputedStyle(element.node);
      element.typingMask=style.backgroundImage!=='none'&&(style.backgroundClip==='text'||style.webkitBackgroundClip==='text');
      if(element.typingMask){element.savedTypingMask={value:element.node.style.getPropertyValue('mask-image'),priority:element.node.style.getPropertyPriority('mask-image')};}
      let weight=0;
      const glyphs=[];
      for(const [node,text] of element.textNodes) {
        const range=this.engine.doc.createRange();range.setStart(node,0);range.setEnd(node,text.length);
        this.highlight?.add(range);
        const segments=this.segmenter?[...this.segmenter.segment(text)].map(s=>({text:s.segment,end:s.index+s.segment.length})):Array.from(text).map((char,i,all)=>({text:char,end:all.slice(0,i+1).join('').length}));
        for(const segment of segments) {
          const punctuation=/[,.!?;:]/.test(segment.text)?1.7:/\s/.test(segment.text)?.42:1;
          const variation=.88+(segment.text.codePointAt(0)%11)*.024;
          weight+=punctuation*variation;
          glyphs.push({node,end:segment.end,weight});
        }
        element.typingRuns||=[];element.typingRuns.push({node,text,range});
      }
      element.typing={glyphs,total:weight,index:-1,caret:null};
      if(element.typingMask)this.maskTypedText(element);
    }
    clearText(element) {
      for(const run of element.typingRuns||[])this.highlight?.delete(run.range);
      if(element.savedTypingMask){const saved=element.savedTypingMask;if(saved.value)element.node.style.setProperty('mask-image',saved.value,saved.priority);else element.node.style.removeProperty('mask-image');element.savedTypingMask=null;}
      element.typingRuns=[];element.typing=null;
    }
    maskTypedText(element) {
      const box=element.node.getBoundingClientRect(),rects=[];
      for(const run of element.typingRuns||[]) {
        if(!run.range.startOffset)continue;
        const range=this.engine.doc.createRange();range.setStart(run.node,0);range.setEnd(run.node,run.range.startOffset);
        for(const r of range.getClientRects())rects.push(`<rect x="${r.x-box.x-.5}" y="${r.y-box.y-.5}" width="${r.width+1}" height="${r.height+1}" fill="white"/>`);
      }
      const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${Math.max(1,box.w)}" height="${Math.max(1,box.h)}">${rects.join('')}</svg>`;
      element.node.style.setProperty('mask-image',`url("data:image/svg+xml,${encodeURIComponent(svg)}")`);
    }
    type(element,amount,agent) {
      const typing=element.typing;if(!typing)return;
      const weight=typing.total*amount;
      let low=0,high=typing.glyphs.length;
      while(low<high){const mid=(low+high)>>1;if(typing.glyphs[mid].weight<=weight)low=mid+1;else high=mid;}
      const index=low-1;
      if(index!==typing.index) {
        for(const run of element.typingRuns) {
          let offset=0;
          for(let i=Math.max(0,typing.index+1);i<=index;i++)if(typing.glyphs[i].node===run.node)offset=typing.glyphs[i].end;
          if(index<typing.index)offset=0;
          if(offset||index<typing.index)run.range.setStart(run.node,offset);
        }
        typing.index=index;
        if(element.typingMask)this.maskTypedText(element);
        this.engine.sound.play('type',agent.x/this.engine.width);
      }
      const glyph=typing.glyphs[Math.max(0,index)];
      if(glyph) {
        const caret=this.engine.doc.createRange();
        caret.setStart(glyph.node,index<0?0:glyph.end);caret.collapse(true);
        const rect=caret.getBoundingClientRect();
        if(rect.height)typing.caret={x:rect.x,y:rect.y,h:rect.height};
      }
      // Older Chromium without Custom Highlights still preserves DOM layout.
      if(!this.highlight)this.clip(element,amount,1);
    }
    clip(element,xProgress,yProgress) {
      const full=this.engine.box(element),r=this.workRect(element);
      const left=Math.max(0,r.x-full.x),top=Math.max(0,r.y-full.y);
      const right=Math.max(0,full.w-left-r.w*xProgress),bottom=Math.max(0,full.h-top-r.h*yProgress);
      element.node.style.clipPath=`inset(${top}px ${right}px ${bottom}px ${left}px)`;
    }
    frameReady(agent,task,element) {
      if(task.scaffolded)return;
      task.scaffolded=true;task.frameReadyAt=this.engine.time;
      task.handoffPoint={...agent.pose};
      this.engine.restoreClip(element);
      this.engine.emit('frame-ready',{agent:agent.id,task:task.id,element:element.id});
    }
    update(agent,dt) {
      const task=agent.task,e=this.engine.elements.get(task.element),r=this.workRect(e);
      task.elapsed+=dt;
      const arrival=clamp(task.elapsed/task.travel,0,1);
      if(arrival<1) {
        const end=this.anchor(e,task),t=ease(arrival),dx=end.x-task.origin.x,dy=end.y-task.origin.y,length=Math.hypot(dx,dy)||1,bend=Math.sin(t*Math.PI)*task.bend;
        agent.pose={x:task.origin.x+dx*t-dy/length*bend,y:task.origin.y+dy*t+dx/length*bend};
        agent.focus=end;agent.phase='Approaching';agent.tool='arrow';return;
      }
      const p=clamp((task.elapsed-task.travel)/task.build,0,1);
      task.progress=p;
      const at=this.anchor(e,task);
      agent.pose={...at};agent.focus=at;
      if(!task.pressed) {
        task.pressed=true;this.effects.push({kind:'press',from:at,color:agent.color,start:this.engine.time,duration:.23});
        this.engine.sound.play('click',at.x/this.engine.width);
      }
      agent.phase=p<.08?'Select':actions[task.operation];agent.tool='arrow';
      if(task.operation==='verify') {
        const t=ease(phase(p,.12,.8));
        agent.pose={x:r.x+lerp(Math.min(90,r.w*.5),Math.min(190,r.w*.75),t),y:r.y+lerp(8,Math.min(r.h*.5,70),t)};
      } else if(task.operation==='duplicate') {
        const master=this.sourceRect(e),t=ease(phase(p,.12,.64));
        task.drawProgress=t;
        agent.tool=p<.65?'copy':e.textNodes.length?'text':'arrow';
        if(p>=.08&&p<.64)agent.phase='Alt-drag';
        agent.pose={x:lerp(master.x,r.x,t),y:lerp(master.y,r.y,t)};
        if(p>=.6&&!task.paint){e.node.setAttribute('data-sw-state','active');task.paint=true;}
        if(p<.64)this.clip(e,0,0);
        else {
          this.engine.restoreClip(e);
          if(e.textNodes.length){agent.phase='Type';this.type(e,phase(p,.64,.96),agent);}
          else if(e.kind==='image')this.clip(e,1,phase(p,.64,.94));
          if(p>=.7&&e.kind==='container')this.frameReady(agent,task,e);
        }
      } else if(task.operation==='type') {
        const drag=ease(phase(p,.06,.28));task.drawProgress=drag;
        if(p>=.08&&p<.3)agent.phase='Text frame';
        agent.tool=p<.3?'cross':'text';
        // After drawing a text frame, the mouse rests at the release point.
        // The insertion caret advances independently with actual keyboard input.
        agent.pose={x:r.x+r.w*drag,y:r.y+r.h*drag};
        if(p>=.3&&!task.paint){e.node.setAttribute('data-sw-state','active');task.paint=true;this.engine.restoreClip(e);}
        if(p>=.3)this.type(e,phase(p,.3,.95),agent);
      } else if(task.operation==='place') {
        const drag=ease(phase(p,.06,.34)),reveal=ease(phase(p,.4,.92));task.drawProgress=drag;
        if(p>=.08&&p<.36)agent.phase='Image frame';
        agent.tool=p<.36?'cross':'arrow';
        agent.pose={x:r.x+r.w*drag,y:r.y+r.h*drag};
        if(p>=.36&&!task.paint){e.node.setAttribute('data-sw-state','active');task.paint=true;}
        if(task.paint)this.clip(e,1,reveal);
      } else if(task.operation==='stroke') {
        const t=ease(phase(p,.08,.88));task.drawProgress=t;agent.tool='pen';
        agent.pose={x:r.x+r.w*t,y:r.y+r.h*t};
        if(!task.paint){e.node.setAttribute('data-sw-state','active');task.paint=true;}
        this.clip(e,t,1);
      } else {
        const drag=ease(phase(p,.06,.67));task.drawProgress=drag;agent.tool=p<.7?'cross':'arrow';
        agent.pose={x:r.x+r.w*drag,y:r.y+r.h*drag};
        if(!task.paint){this.clip(e,0,0);e.node.setAttribute('data-sw-state','active');task.paint=true;}
        if(p<.67)this.clip(e,drag,drag);
        else {this.frameReady(agent,task,e);agent.phase=p<.86?'Align':'Release';}
      }
      if(p>=1)this.complete(agent,task,e);
    }

  }
  
})();

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
    complete(agent,task,element) {
      agent.x=agent.pose.x;agent.y=agent.pose.y;task.handoffPoint={...agent.pose};
      if(task.operation==='verify') {
        const broken=[...this.engine.doc.images].filter(img=>!img.complete||!img.naturalWidth);
        if(broken.length){task.status='failed';this.engine.failed++;agent.task=null;agent.lastWorked=this.engine.time;this.engine.emit('task-error',{task:task.id,label:`${broken.length} images failed validation`});return;}
      }
      this.clearText(element);element.node.removeAttribute('data-sw-state');this.engine.restoreClip(element);
      task.status='complete';task.completedAt=this.engine.time;this.engine.done++;agent.completed++;
      agent.task=null;agent.lastWorked=this.engine.time;agent.phase='Handing off';
      this.engine.history.push({task:task.id,agent:agent.id,start:this.engine.time-task.elapsed,end:this.engine.time});
      this.effects.push({kind:'settle',rect:this.workRect(element),color:agent.color,start:this.engine.time,duration:.28});
      this.engine.sound.play(task.operation,agent.x/this.engine.width);
      this.engine.emit('completed',{agent:agent.id,task:task.id,completed:this.engine.done,total:this.engine.tasks.length,label:task.label});
    }
    render(ctx) {
      const engine=this.engine,active=engine.agents.filter(a=>a.task);
      const drawing=active.filter(a=>a.task.progress>0&&a.task.operation!=='verify');
      if(drawing.length) {
        ctx.save();ctx.globalAlpha=.65;ctx.fillStyle='#252c35';ctx.fillRect(0,0,engine.width,17);
        ctx.font='9px Segoe UI';ctx.fillStyle='#b5bfce';ctx.strokeStyle='#7f8b9c';
        for(let x=50;x<engine.width;x+=50){ctx.beginPath();ctx.moveTo(x,12);ctx.lineTo(x,17);ctx.stroke();ctx.fillText(String(x),x+3,9);}
        ctx.restore();
      }
      let badges=0;
      for(const a of active) {
        const t=a.task,p=t.progress||0;if(p<=0)continue;
        const e=engine.elements.get(t.element),r=this.workRect(e),d=t.drawProgress||0;
        ctx.save();ctx.strokeStyle=a.color;ctx.lineWidth=.9;ctx.globalAlpha=.85;
        if(t.operation==='verify') {
          ctx.setLineDash([3,3]);ctx.strokeRect(r.x,r.y,r.w,r.h);
        } else if(t.operation==='stroke') {
          ctx.beginPath();ctx.moveTo(r.x,r.y);ctx.lineTo(a.pose.x,a.pose.y);ctx.stroke();ctx.fillStyle=a.color;ctx.fillRect(r.x-2,r.y-2,4,4);
        } else {
          let box={...r,w:r.w*d,h:r.h*d};
          if(t.operation==='duplicate') {
            const master=this.sourceRect(e);box={x:lerp(master.x,r.x,d),y:lerp(master.y,r.y,d),w:lerp(master.w,r.w,d),h:lerp(master.h,r.h,d)};
            ctx.setLineDash([3,3]);ctx.globalAlpha=.24;ctx.strokeRect(master.x,master.y,master.w,master.h);ctx.setLineDash([]);ctx.globalAlpha=.85;
          }
          if(t.operation==='place'&&p<.4){ctx.fillStyle='#8993a522';ctx.fillRect(box.x,box.y,box.w,box.h);ctx.beginPath();ctx.moveTo(box.x,box.y);ctx.lineTo(box.x+box.w,box.y+box.h);ctx.moveTo(box.x+box.w,box.y);ctx.lineTo(box.x,box.y+box.h);ctx.stroke();}
          ctx.strokeRect(box.x,box.y,box.w,box.h);
          if(p<.75)for(const [x,y] of [[box.x,box.y],[box.x+box.w,box.y],[box.x,box.y+box.h],[box.x+box.w,box.y+box.h]]){ctx.fillStyle='#f2f5fa';ctx.fillRect(x-1.5,y-1.5,3,3);ctx.strokeRect(x-1.5,y-1.5,3,3);}
          if(p<.68&&badges++<2&&box.w>45&&box.h>12) {
            const text=`${Math.round(box.w)} × ${Math.round(box.h)}`;ctx.font='10px Segoe UI';const width=ctx.measureText(text).width+10;
            const x=clamp(box.x+box.w-width,22,engine.width-width-8),y=clamp(box.y+box.h+5,22,engine.height-22);
            ctx.fillStyle='#232b35';ctx.fillRect(x,y,width,17);ctx.fillStyle='#f3f6fc';ctx.fillText(text,x+5,y+12);
          }
        }
        if(e.typing?.caret&&p>.3) {
          const caret=e.typing.caret;if(caret.y+caret.h>0&&caret.y<engine.height){ctx.globalAlpha=.9;ctx.beginPath();ctx.moveTo(caret.x,Math.max(0,caret.y));ctx.lineTo(caret.x,Math.min(engine.height,caret.y+caret.h));ctx.stroke();}
        }
        // Short, local snapping guides replace full-screen red crosshairs.
        if((t.operation==='duplicate'||a.phase==='Align')&&p>.7&&p<.92){ctx.globalAlpha=.5;ctx.strokeStyle='#d87973';ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(Math.max(20,r.x-28),r.y);ctx.lineTo(Math.min(engine.width-8,r.x+r.w+28),r.y);ctx.stroke();}
        ctx.restore();
      }
      this.effects=this.effects.filter(effect=>engine.time-effect.start<effect.duration);
      for(const effect of this.effects) {
        const p=clamp((engine.time-effect.start)/effect.duration,0,1);ctx.save();ctx.strokeStyle=effect.color;ctx.lineWidth=1;ctx.globalAlpha=(1-p)*.45;
        if(effect.kind==='press'){ctx.beginPath();ctx.arc(effect.from.x,effect.from.y,3+8*p,0,Math.PI*2);ctx.stroke();}
        else if(effect.kind==='settle'){const r=effect.rect;ctx.strokeRect(r.x,r.y,r.w,r.h);}
        else if(effect.kind==='handoff'&&Math.hypot(effect.from.x-effect.to.x,effect.from.y-effect.to.y)<320){ctx.setLineDash([2,4]);ctx.beginPath();ctx.moveTo(effect.from.x,effect.from.y);ctx.lineTo(effect.to.x,effect.to.y);ctx.stroke();}
        ctx.restore();
      }
    }
  }
  window.TaskChoreography=TaskChoreography;
})();

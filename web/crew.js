/* A small, demand-driven crew. Cursors enter to work and retire when unneeded. */
(() => {
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const smooth=t=>t*t*t*(t*(t*6-15)+10);
  const identities=[
    ['Ada','Layout',['draw'],'#ee826b'],['Grace','Type',['type'],'#a897ed'],
    ['Linus','Components',['duplicate','remove'],'#54b8df'],['Hedy','Assets',['place','place_media'],'#67bf9e'],
    ['Alan','Inspect',['verify'],'#d7b569'],['Radia','Navigation',['type','draw'],'#d98db5'],
    ['Margaret','Structure',['draw'],'#7fa9d1'],['Ken','Details',['stroke','draw'],'#b4bd70'],
    ['Katherine','Type',['type'],'#c1a0da'],['Dennis','Components',['duplicate'],'#d7a378'],
    ['Barbara','Style',['draw','place'],'#82bcae'],['Guido','Layout',['draw'],'#8fa9d4']
  ];
  class WorkingCrew {
    constructor(engine) {
      this.engine=engine;
      const count=clamp(Number(engine.settings.agents)||8,2,12);
      this.members=Array.from({length:count},(_,id)=>{
        const [name,role,preferred,color]=identities[id];
        const home=this.home(id);
        return {id,name,role,preferred,color,x:home.x,y:home.y,vx:0,vy:0,opacity:0,
          completed:0,task:null,phase:'Available',personality:.94+engine.random()*.14,
          tool:'arrow',lastWorked:-100,focus:null,pose:null,labelBox:null,labelAlpha:0,trail:[]};
      });
      this.lastDispatch=-1;
    }
    home(id) {
      const left=id%2===0;
      return {x:left?-24:this.engine.width+24,y:clamp(70+Math.floor(id/2)*82,40,this.engine.height-40)};
    }
    get capacity(){return Math.min(this.members.length,clamp(Math.floor(this.engine.width*this.engine.height/200000),2,4));}
    get uiScale(){return 1/Math.max(1,this.engine.presentation?.enabled?this.engine.presentation.matrix().scale:1);}
    cost(agent,task) {
      const e=this.engine.elements.get(task.element),r=this.engine.choreography.workRect(e);
      let preference=agent.preferred.includes(task.operation)?0:185;
      if(agent.id===5&&['a','button','input','select','nav'].includes(e.tag))preference-=130;
      if(agent.id===7&&r.w*r.h<14000)preference-=60;
      if(agent.id===6&&r.w*r.h>140000)preference-=65;
      const distance=Math.hypot(agent.x-r.x,agent.y-r.y);
      return preference+distance*.12+agent.completed*7+(agent.opacity<.1?25:0);
    }
    collides(task) {
      const e=this.engine.elements.get(task.element),point=this.engine.choreography.anchor(e,task);
      return this.members.some(a=>a.task&&Math.hypot((a.pose?.x??a.x)-point.x,(a.pose?.y??a.y)-point.y)<42);
    }
    dispatch() {
      const engine=this.engine;
      const available=engine.tasks.filter(t=>engine.ready(t)&&engine.isVisible(engine.elements.get(t.element))&&
        (t.operation!=='verify'||!engine.settings.auto_tour||engine.camera.atEnd));
      let active=this.members.filter(a=>a.task).length;
      while(active<this.capacity) {
        let pick=null,best=Infinity;
        for(const task of available) {
          if(task.status!=='pending'||this.collides(task))continue;
          const specialists=this.members.filter(agent=>agent.preferred.includes(task.operation));
          for(const agent of this.members) {
            if(agent.task)continue;
            if(specialists.length&&!specialists.includes(agent))continue;
            const cost=this.cost(agent,task);
            if(cost<best){best=cost;pick={agent,task};}
          }
        }
        if(!pick)break;
        engine.assign(pick.agent,pick.task);
        active++;
      }
    }
    animate(dt) {
      const e=this.engine;
      for(const a of this.members) {
        const oldX=a.x,oldY=a.y;
        const intro=e.time<e.introDuration&&a.id<Math.min(3,this.members.length)&&e.settings.intro!==false&&!e.settings.reduced_motion;
        let targetOpacity=0;
        if(a.task&&a.pose) {
          // The task trajectory IS the cursor trajectory: no second spring
          // delays a mouse behind a frame that is already being drawn.
          a.x=a.pose.x;a.y=a.pose.y;targetOpacity=1;
        } else if(intro) {
          const t=clamp(e.time/e.introDuration,0,1),k=smooth(t);
          const angle=a.id*Math.PI*2/3+e.time*.8;
          const home=this.home(a.id);
          a.x=home.x+(e.width*.5+Math.cos(angle)*62-home.x)*k;
          a.y=home.y+(e.height*.5+Math.sin(angle)*42-home.y)*k;
          a.tool='arrow';a.phase='Preparing';targetOpacity=Math.min(1,t*5);
        } else {
          const elapsed=e.time-a.lastWorked;
          const linger=elapsed<.22&&!e.finished;
          // Retire at the release point. Flying idle pointers across the site
          // was both distracting and much faster than deliberate work motion.
          if(a.opacity<.02){const home=this.home(a.id);a.x=home.x;a.y=home.y;}
          targetOpacity=linger?.65:0;
          a.tool='arrow';a.phase=linger?'Handing off':'Available';
        }
        a.opacity+=(targetOpacity-a.opacity)*(1-Math.exp(-dt*(targetOpacity>a.opacity?14:9)));
        a.vx=(a.x-oldX)/Math.max(dt,.001);a.vy=(a.y-oldY)/Math.max(dt,.001);
        if(a.task&&a.phase==='Approaching'&&a.opacity>.25&&!e.settings.reduced_motion){
          a.trail.push({x:a.x,y:a.y,time:e.time});
          if(a.trail.length>10)a.trail.shift();
        }
        a.trail=a.trail.filter(point=>e.time-point.time<.12);
      }
      // At most two brief handoffs can coexist with the working crew.
      const idle=this.members.filter(a=>!a.task&&a.opacity>.12).sort((a,b)=>b.lastWorked-a.lastWorked);
      if(e.time>=e.introDuration)for(const a of idle.slice(2))a.opacity=Math.min(a.opacity,.08);
      this.layoutLabels(dt);
    }
    layoutLabels(dt) {
      const e=this.engine,unit=this.uiScale,occupied=[];
      const active=this.members.filter(a=>a.task&&a.opacity>.1).sort((a,b)=>b.opacity-a.opacity||a.id-b.id);
      for(const a of this.members)if(!active.includes(a)){a.labelAlpha=0;a.labelBox=null;}
      for(const a of active){
        const w=188*unit,h=58*unit,gap=18*unit;
        const candidates=[{x:a.x+gap,y:a.y+gap},{x:a.x-w-gap,y:a.y+gap},{x:a.x+gap,y:a.y-h-gap},{x:a.x-w-gap,y:a.y-h-gap}];
        const free=p=>p.x>=10&&p.x+w<e.width-10&&p.y>=10&&p.y+h<e.height-10&&!occupied.some(b=>p.x<b.x+b.w+6&&p.x+w+6>b.x&&p.y<b.y+b.h+6&&p.y+h+6>b.y);
        // Keep the chosen side until it no longer fits. Labels follow a damped
        // position; their settling never delays the actual tool or DOM reveal.
        let index=a.labelSide??0;
        if(!free(candidates[index]))index=candidates.findIndex(free);
        const target=index>=0?candidates[index]:null;
        // A retiring card must not fade through another worker's current card
        // when all four placements are obstructed.
        if(!target){a.labelAlpha=0;continue;}
        if(target){
          a.labelSide=index;
          const k=e.settings.reduced_motion?1:1-Math.exp(-dt*22),old=a.labelBox;
          a.labelBox={x:old?old.x+(target.x-old.x)*k:target.x,y:old?old.y+(target.y-old.y)*k:target.y,w,h};
          a.labelBox.x=clamp(a.labelBox.x,10,e.width-w-10);a.labelBox.y=clamp(a.labelBox.y,10,e.height-h-10);
          if(free(a.labelBox))occupied.push(a.labelBox);else {a.labelAlpha=0;continue;}
        }
        a.labelAlpha+=((target?1:0)-a.labelAlpha)*(1-Math.exp(-dt*16));
      }
    }
    render(ctx) {
      const unit=this.uiScale;
      const members=this.members.filter(a=>a.opacity>.035).sort((a,b)=>Number(!!a.task)-Number(!!b.task));
      for(const a of members) {
        if(a.x<-22||a.x>this.engine.width+22||a.y<-22||a.y>this.engine.height+22)continue;
        if(a.trail.length>1){
          ctx.save();ctx.strokeStyle=a.color;ctx.lineWidth=1.5*unit;
          for(let i=1;i<a.trail.length;i++){ctx.globalAlpha=a.opacity*.12*i/a.trail.length;ctx.beginPath();ctx.moveTo(a.trail[i-1].x,a.trail[i-1].y);ctx.lineTo(a.trail[i].x,a.trail[i].y);ctx.stroke();}ctx.restore();
        }
        ctx.save();ctx.globalAlpha=a.opacity;
        ctx.translate(a.x,a.y);const size=(this.engine.settings.cursor_size||1)*unit;ctx.scale(size,size);
        ctx.shadowColor='#08131e55';ctx.shadowBlur=2;ctx.shadowOffsetY=1;
        ctx.fillStyle=a.color;ctx.strokeStyle='#fff';ctx.lineWidth=1.25;ctx.lineJoin='round';ctx.lineCap='round';
        ctx.beginPath();
        if(a.tool==='cross') {
          ctx.shadowBlur=0;
          ctx.moveTo(-6,0);ctx.lineTo(6,0);ctx.moveTo(0,-6);ctx.lineTo(0,6);ctx.stroke();
          ctx.strokeStyle=a.color;ctx.lineWidth=1;ctx.stroke();
        } else if(a.tool==='text') {
          ctx.shadowBlur=0;
          ctx.moveTo(-3,-7);ctx.lineTo(3,-7);ctx.moveTo(0,-7);ctx.lineTo(0,7);ctx.moveTo(-3,7);ctx.lineTo(3,7);ctx.stroke();
          ctx.strokeStyle=a.color;ctx.lineWidth=.8;ctx.stroke();
        } else if(a.tool==='pen') {
          ctx.moveTo(0,0);ctx.lineTo(11,4);ctx.lineTo(15,10);ctx.lineTo(10,15);ctx.lineTo(4,11);ctx.closePath();ctx.fill();ctx.stroke();
          ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(7,7);ctx.stroke();
        } else {
          if(a.tool==='copy'){ctx.strokeRect(7,11,6,6);ctx.strokeRect(10,14,6,6);}
          ctx.moveTo(0,0);ctx.lineTo(3.8,15);ctx.lineTo(8,9.5);ctx.lineTo(14,7.5);ctx.closePath();ctx.fill();ctx.stroke();
        }
        ctx.restore();
        if(this.engine.settings.names===false||!a.task||!a.labelBox||a.labelAlpha<.05)continue;
        const box=a.labelBox,task=a.task;
        ctx.save();ctx.globalAlpha=a.opacity*a.labelAlpha;
        ctx.translate(box.x,box.y);ctx.scale(unit,unit);
        ctx.shadowColor='#06101725';ctx.shadowBlur=14;ctx.shadowOffsetY=4;
        ctx.fillStyle='#121b22f5';ctx.beginPath();ctx.roundRect(0,0,188,58,9);ctx.fill();
        ctx.shadowBlur=0;ctx.shadowOffsetY=0;ctx.strokeStyle='#ffffff21';ctx.lineWidth=.8;ctx.stroke();
        ctx.fillStyle=a.color;ctx.beginPath();ctx.arc(14,15,3,0,Math.PI*2);ctx.fill();
        ctx.font='600 11px Segoe UI';ctx.fillStyle='#f1f5f5';ctx.fillText(a.name,23,19);
        ctx.font='10px Segoe UI';ctx.fillStyle='#9aaeb8';
        const roleWidth=ctx.measureText(a.role).width;ctx.fillText(a.role,176-roleWidth,19);
        const stage=a.phase==='Approaching'?'Locating':task.stage==='inspect'?'Inspecting':task.stage==='review'?'Reviewing':task.intent?.verb||a.phase;
        const subject=task.intent?.subject||'element';
        let caption=stage+' '+subject;
        ctx.font='10px Segoe UI';while(ctx.measureText(caption).width>164&&caption.length>8)caption=caption.slice(0,-2)+'…';
        ctx.fillStyle='#d5e1e6';ctx.fillText(caption,12,36);
        ctx.fillStyle='#ffffff14';ctx.beginPath();ctx.roundRect(12,47,164,2,1);ctx.fill();
        ctx.fillStyle=a.color;ctx.beginPath();ctx.roundRect(12,47,Math.max(2,164*(task.progress||0)),2,1);ctx.fill();
        ctx.restore();
      }
    }
  }
  window.WorkingCrew=WorkingCrew;
})();

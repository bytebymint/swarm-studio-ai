/* A small, demand-driven crew. Cursors enter to work and retire when unneeded. */
(() => {
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const smooth=t=>t*t*t*(t*(t*6-15)+10);
  const identities=[
    ['Ada','Layout',['draw'],'#ee826b'],['Grace','Type',['type'],'#a897ed'],
    ['Linus','Components',['duplicate'],'#54b8df'],['Hedy','Assets',['place','place_media'],'#67bf9e'],
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
          tool:'arrow',lastWorked:-100,focus:null,pose:null,labelBox:null};
      });
      this.lastDispatch=-1;
    }
    home(id) {
      const left=id%2===0;
      return {x:left?-24:this.engine.width+24,y:clamp(70+Math.floor(id/2)*82,40,this.engine.height-40)};
    }
    get capacity(){return Math.min(this.members.length,clamp(Math.floor(this.engine.width*this.engine.height/145000),2,8));}
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
          for(const agent of this.members) {
            if(agent.task)continue;
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
      }
      // At most two brief handoffs can coexist with the working crew.
      const idle=this.members.filter(a=>!a.task&&a.opacity>.12).sort((a,b)=>b.lastWorked-a.lastWorked);
      if(e.time>=e.introDuration)for(const a of idle.slice(2))a.opacity=Math.min(a.opacity,.08);
    }
    render(ctx) {
      const occupied=[];
      const members=this.members.filter(a=>a.opacity>.035).sort((a,b)=>Number(!!a.task)-Number(!!b.task));
      for(const a of members) {
        if(a.x<-22||a.x>this.engine.width+22||a.y<-22||a.y>this.engine.height+22)continue;
        ctx.save();ctx.globalAlpha=a.opacity;
        ctx.translate(a.x,a.y);const size=(this.engine.settings.cursor_size||1)*.88;ctx.scale(size,size);
        ctx.fillStyle=a.color;ctx.strokeStyle='#fff';ctx.lineWidth=1.25;ctx.lineJoin='round';ctx.lineCap='round';
        ctx.beginPath();
        if(a.tool==='cross') {
          ctx.moveTo(-6,0);ctx.lineTo(6,0);ctx.moveTo(0,-6);ctx.lineTo(0,6);ctx.stroke();
          ctx.strokeStyle=a.color;ctx.lineWidth=1;ctx.stroke();
        } else if(a.tool==='text') {
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
        if(this.engine.settings.names===false||!a.task)continue;
        const action=a.phase==='Approaching'?a.role:a.phase;
        const text=a.name+' · '+action;
        ctx.save();ctx.globalAlpha=a.opacity*.95;ctx.font='500 10px Segoe UI';
        const width=ctx.measureText(text).width+16,height=19;
        const candidates=[{x:a.x+14,y:a.y+15},{x:a.x-width-12,y:a.y+15},{x:a.x+14,y:a.y-28},{x:a.x-width-12,y:a.y-28}];
        let label=candidates.find(p=>p.x>20&&p.x+width<this.engine.width-8&&p.y>20&&p.y+height<this.engine.height-8&&!occupied.some(b=>p.x<b.x+b.w&&p.x+width>b.x&&p.y<b.y+b.h&&p.y+height>b.y));
        if(!label){ctx.restore();continue;}
        occupied.push({x:label.x,y:label.y,w:width,h:height});a.labelBox={...label,w:width,h:height};
        ctx.fillStyle='#232b35';ctx.beginPath();ctx.roundRect(label.x,label.y,width,height,3);ctx.fill();
        ctx.fillStyle=a.color;ctx.fillRect(label.x+4,label.y+5,2,9);
        ctx.fillStyle='#f4f6fb';ctx.fillText(text,label.x+10,label.y+13);ctx.restore();
      }
    }
  }
  window.WorkingCrew=WorkingCrew;
})();

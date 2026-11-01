/* A small, demand-driven crew. Cursors enter to work and retire when unneeded. */
(() => {
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const smooth=t=>t*t*t*(t*(t*6-15)+10);
  const identities=[
    ['Ada','Layout',['draw'],'#ee826b'],['Grace','Type',['type'],'#a897ed'],
    ['Linus','Components',['duplicate'],'#54b8df'],['Hedy','Assets',['place'],'#67bf9e'],
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

  }
  
})();

/* A continuous recording lens over the unchanged reconstruction viewport. */
(() => {
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const damp=(value,target,velocity,time,dt,maxSpeed=Infinity)=>{
    const omega=2/Math.max(.1,time),x=omega*dt,decay=1/(1+x+.48*x*x+.235*x*x*x);
    let delta=clamp(value-target,-maxSpeed*time,maxSpeed*time);
    const destination=value-delta,temp=(velocity+omega*delta)*dt;
    const next=destination+(delta+temp)*decay;
    const speed=(velocity-omega*temp)*decay;
    if((target-value>0)===(next>target))return {value:target,velocity:0};
    return {value:next,velocity:speed};
  };

  class MoviePresentation {
    constructor(engine){this.engine=engine;this.enabled=false;this.logicalWidth=0;this.logicalHeight=0;this.originalStyle=engine.frame.style.cssText;}
    enable(width,height){
      this.enabled=true;this.logicalWidth=width;this.logicalHeight=height;
      Object.assign(this.engine.frame.style,{position:'absolute',left:'0',top:'0',width:width+'px',height:height+'px',transformOrigin:'0 0',willChange:'transform'});
    }
    disable(){this.enabled=false;this.engine.frame.style.cssText=this.originalStyle;this.engine.boundsCache?.clear();}
    matrix(){
      const e=this.engine,pose=e.director?.pose||{x:e.width/2,y:e.height/2,zoom:1};
      const base=Math.min(innerWidth/e.width,innerHeight/e.height),scale=base*pose.zoom;
      const halfW=innerWidth/(2*scale),halfH=innerHeight/(2*scale);
      const x=halfW>=e.width/2?e.width/2:clamp(pose.x,halfW,e.width-halfW);
      const y=halfH>=e.height/2?e.height/2:clamp(pose.y,halfH,e.height-halfH);
      return {scale,x:innerWidth/2-x*scale,y:innerHeight/2-y*scale,centerX:x,centerY:y,zoom:pose.zoom};
    }
    apply(){
      const m=this.matrix();
      this.engine.frame.style.transform=`matrix(${m.scale.toFixed(7)},0,0,${m.scale.toFixed(7)},${m.x.toFixed(5)},${m.y.toFixed(5)})`;
      return m;
    }
  }

  class RecordingDirector {
    constructor(engine,maxZoom=3){
      this.engine=engine;this.maxZoom=clamp(maxZoom,1,3);this.time=0;
      this.pose={x:engine.width/2,y:engine.height/2,zoom:1};
      this.velocity={x:0,y:0,zoom:0};this.target={...this.pose};
      this.state='wide';this.holdUntil=1.7;this.travelRequested=false;
      this.focus=null;this.pending=null;this.focusStarted=0;this.finishAt=null;this.finished=false;this.shots=[];
    }
    allowScroll(){
      this.travelRequested=true;
      this.target.zoom=1;this.state='pullback';
      return this.pose.zoom<1.025;
    }
    candidate(){
      const e=this.engine;
      let best=null,score=-Infinity;
      for(const agent of e.agents){
        const task=agent.task;if(!task||task.operation==='verify')continue;
        const element=e.elements.get(task.element);if(!element?.node||!e.isVisible(element))continue;
        const r=e.choreography.workRect(element),area=r.w*r.h;
        if(area>e.width*e.height*.62)continue;
        if(task.operation==='draw'&&r.w>e.width*.72)continue;
        const remaining=Math.max(0,task.travel+task.build-task.elapsed);
        if(remaining<.7)continue;
        let value=({type:6,place:5,duplicate:4,draw:2,stroke:1}[task.operation]||0)+Math.min(3,remaining);
        if(task.operation==='type'&&parseFloat(element.fontSize)>25)value+=2;
        if(task.id===this.focus?.id)value+=2;
        if(value>score){score=value;best={id:task.id,element:task.element,rect:r,agent:agent.id};}
      }
      return best;
    }
    compose(focus){
      const e=this.engine,element=e.elements.get(focus.element),r=e.choreography.workRect(element);
      const left=Math.max(0,r.x-45);
      const top=Math.max(0,r.y-55);
      const right=Math.min(e.width,r.x+r.w+100);
      const bottom=Math.min(e.height,r.y+r.h+65);
      const zoom=clamp(Math.min(e.width/Math.max(150,right-left),e.height/Math.max(100,bottom-top))*.94,Math.min(1.2,this.maxZoom),this.maxZoom);
      return {x:(left+right)/2,y:(top+bottom)/2,zoom};
    }
    choose(focus){
      this.focus=focus;this.focusStarted=this.time;this.state='focus';
      this.target=this.compose(focus);this.holdUntil=this.time+2.6;
      this.shots.push({time:Number(this.time.toFixed(4)),task:focus.id,zoom:Number(this.target.zoom.toFixed(4)),x:this.target.x,y:this.target.y});
    }
    taskDelta(agent,dt){
      // Let a selected edit remain legible while the lens arrives. This is
      // deterministic movie pacing; ordinary interactive playback is untouched.
      return this.state==='focus'&&agent.task?.id===this.focus?.id&&this.time-this.focusStarted<1.3?dt*.22:dt;
    }
    update(dt){
      this.time+=dt;const e=this.engine;
      const candidate=this.candidate();
      if(e.finished){
        this.finishAt??=this.time;this.target={x:e.width/2,y:e.height/2,zoom:1};this.state='ending';
      } else if(e.camera.move){
        this.state='travel';this.target={x:e.width/2,y:e.height/2,zoom:1};this.travelRequested=false;this.focus=null;this.holdUntil=this.time+.65;
      } else if(this.travelRequested){
        this.state='pullback';this.target={x:e.width/2,y:e.height/2,zoom:1};
      } else if(this.state==='pullback'){
        this.target={x:e.width/2,y:e.height/2,zoom:1};
        if(this.pose.zoom<1.035){this.state='wide';this.holdUntil=this.time+.3;}
      } else if(this.time>=this.holdUntil&&candidate){
        const previous=this.focus&&e.byId.get(this.focus.id);
        if(!this.focus||previous?.status!=='active'||this.time-this.focusStarted>5.5){
          if(this.focus&&Math.hypot(this.target.x-this.compose(candidate).x,this.target.y-this.compose(candidate).y)>100){
            this.pending=candidate;this.state='pullback';this.target={x:e.width/2,y:e.height/2,zoom:1};this.focus=null;
          }else this.choose(candidate);
        }
      }
      if(this.state==='wide'&&this.pending&&this.time>=this.holdUntil){
        const pending=e.byId.get(this.pending.id);
        if(pending?.status==='active')this.choose(this.pending);
        else if(candidate)this.choose(candidate);
        this.pending=null;
      }
      // Critically damped position and logarithmic zoom retain velocity across
      // retargets. No shot is a transform jump or a CSS timer detached from tasks.
      const z=damp(Math.log(this.pose.zoom),Math.log(this.target.zoom),this.velocity.zoom,.72,dt,1.1);
      const x=damp(this.pose.x,this.target.x,this.velocity.x,.85,dt,240);
      const y=damp(this.pose.y,this.target.y,this.velocity.y,.85,dt,180);
      this.pose={x:x.value,y:y.value,zoom:clamp(Math.exp(z.value),1,this.maxZoom)};
      this.velocity={x:x.velocity,y:y.velocity,zoom:z.velocity};
      if(e.finished&&this.time-this.finishAt>2.2&&this.pose.zoom<1.015)this.finished=true;
    }
  }
  window.MoviePresentation=MoviePresentation;
  window.RecordingDirector=RecordingDirector;
})();

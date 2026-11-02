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

})();

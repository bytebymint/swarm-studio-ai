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

  }

})();

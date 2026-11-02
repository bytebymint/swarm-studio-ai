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

})();

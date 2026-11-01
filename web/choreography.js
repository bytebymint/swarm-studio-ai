/* Geometry-driven design-tool interactions. Text stays in its original layout. */
(() => {
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const ease=t=>t*t*t*(t*(t*6-15)+10);
  const phase=(p,a,b)=>clamp((p-a)/(b-a),0,1);
  const lerp=(a,b,t)=>a+(b-a)*t;

})();

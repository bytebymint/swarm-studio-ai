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

})();

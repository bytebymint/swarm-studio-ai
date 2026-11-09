/* Live model operations, rendered by the SAME Studio/WorkingCrew/TaskChoreography. */
(() => {
  'use strict';
  const s=window.Studio,escape=value=>String(value).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
  const base='*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:system-ui,sans-serif}img,svg,video{max-width:100%}button,input,textarea,select{font:inherit}';
  const empty={title:'Your next website starts here',css:'',script:'',blocks:[]};
  const creator={document:structuredClone(empty),pending:[],serial:0,selecting:false,interactive:false,ready:false,ended:false};
  window.Creator=creator;
  creator.emit=(type,data={})=>s.emit(type,data);
  creator.source=(data,interactive=false,readyToken="")=>{
    const nonce=crypto.randomUUID().replaceAll('-','');
    const css=(base+data.css+data.blocks.map(b=>b.css).join('\n')).replace(/<\/style/gi,'<\\/style');
    const markup=data.blocks.map(b=>`<div data-create-block="${escape(b.id)}" style="display:contents">${b.html}</div>`).join('');
    const csp=`default-src 'none';style-src 'unsafe-inline';img-src data: blob:;media-src data: blob:;font-src data:;script-src ${interactive?`'nonce-${nonce}'`:"'none'"};connect-src 'none';object-src 'none';frame-src 'none';base-uri 'none';form-action 'none'`;
    const runtime=`(${function(){
      let selecting=false;
      addEventListener('message',event=>{if(event.source===parent&&event.data?.type==='select')selecting=!!event.data.value;});
      document.addEventListener('click',event=>{if(!selecting)return;event.preventDefault();event.stopImmediatePropagation();const n=event.target,b=n.closest('[data-create-block]');if(b)parent.postMessage({type:'creator-selection',block:b.dataset.createBlock,tag:n.tagName.toLowerCase(),text:(n.innerText||n.getAttribute('aria-label')||'').slice(0,180),id:n.id||''},'*');},true);
      addEventListener('error',event=>parent.postMessage({type:'creator-runtime-error',message:String(event.message).slice(0,240)},'*'));
      document.addEventListener('submit',event=>event.preventDefault());
    }.toString()})();`;
    const js=(runtime+'\n'+`parent.postMessage({type:'creator-preview-loaded',token:${JSON.stringify(readyToken)}},'*');`+'\n'+data.script+'\n'+data.blocks.map(b=>b.js).join('\n')).replace(/<\/script/gi,'<\\/script');
    return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="${escape(csp)}"><title>${escape(data.title)}</title><style id="create-theme">${css}</style></head><body>${markup}${interactive?`<script nonce="${nonce}">${js}</script>`:''}</body></html>`;
  };
  creator.load=async data=>{
    s.running=false;s.restore();creator.pending=[];creator.document=structuredClone(data||empty);creator.serial=0;creator.ended=false;
    creator.preview(false);s.liveOpen=true;s.liveQueue=creator;
    s.frame.removeAttribute('src');
    await new Promise(resolve=>{s.frame.onload=resolve;s.frame.srcdoc=creator.source(creator.document);});
    s.model={elements:[],tasks:[],viewport:{width:innerWidth,height:innerHeight},height:s.frame.contentDocument.body.scrollHeight};
    s.configure({agents:8,intro:false,names:true,auto_tour:true,speed:1,smoothness:1});s.prepare();
    creator.installSelection();creator.ready=true;creator.updateEmpty();creator.emit('creator-ready');
    document.querySelector('#intro p').textContent='Creating, together.';
  };
  creator.updateEmpty=()=>{document.querySelector('#create-empty').hidden=creator.document.blocks.length>0;};
  creator.begin=()=>{
    creator.preview(false);
    const scroll=s.doc.scrollingElement.scrollTop,speed=s.settings.speed;
    s.liveOpen=true;creator.ended=false;s.model.elements=[];s.model.tasks=[];
    s.settings.intro=!creator.document.blocks.length;s.prepare();s.settings.speed=speed;
    s.doc.scrollingElement.scrollTop=scroll;s.boundsCache.clear();
    if(creator.document.blocks.length)s.intro.style.display='none';
  };
  creator.patch=command=>{
    const data=creator.document;
    const previous=command.action==='upsert_block'?structuredClone(data.blocks.find(b=>b.id===command.id)||null):null;
    if(command.action==='plan'){creator.emit('creator-plan',{steps:command.steps});return;}
    if(command.action==='set_title'){data.title=command.title;document.title=command.title;return;}
    if(command.action==='set_script'){data.script=command.js;return;}
    if(command.action==='set_theme')data.css=command.css;
    if(command.action==='upsert_block'){
      const at=data.blocks.findIndex(b=>b.id===command.id),block={id:command.id,html:command.html,css:command.css,js:command.js};
      if(at>=0)data.blocks[at]=block;
      else{const before=data.blocks.findIndex(b=>b.id===command.before);data.blocks.splice(before<0?data.blocks.length:before,0,block);}
    }
    if(command.action==='remove_block')data.blocks=data.blocks.filter(b=>b.id!==command.id);
    creator.pending.push({...structuredClone(command),previous});creator.updateEmpty();creator.flush();
  };
  creator.block=id=>[...s.doc.querySelectorAll('[data-create-block]')].find(n=>n.dataset.createBlock===id);
  creator.retire=root=>{
    const ids=new Set([...s.elements.values()].filter(e=>root===e.node||root.contains(e.node)).map(e=>e.id));
    for(const a of s.agents)if(a.task&&ids.has(a.task.element)){a.task=null;a.lastWorked=s.time;}
    for(const id of ids){const e=s.elements.get(id);s.choreography.clearText(e);s.elements.delete(id);}
    s.tasks=s.tasks.filter(t=>!ids.has(t.element));s.byId=new Map(s.tasks.map(t=>[t.id,t]));
    s.model.elements=s.model.elements.filter(e=>!ids.has(e.id));s.model.tasks=s.model.tasks.filter(t=>!ids.has(t.element));
    s.done=s.tasks.filter(t=>t.status==='complete').length;s.failed=s.tasks.filter(t=>['failed','blocked'].includes(t.status)).length;
  };
  creator.register=(node,operation,keepVisible=false,removalRoot=null)=>{
    const id='create-'+(++creator.serial),rect=node.getBoundingClientRect(),style=s.frame.contentWindow.getComputedStyle(node);
    node.setAttribute('data-sw-id',id);
    const kind=['IMG','SVG','CANVAS'].includes(node.tagName)?'image':node.tagName==='VIDEO'?'media':node.tagName==='HR'?'line':[...node.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())?'text':'container';
    const parent=node.parentElement?.closest('[data-sw-id]')?.getAttribute('data-sw-id');
    const dependency=s.byId.has(parent)?parent:null;
    const e={id,node,parent:dependency,tag:node.tagName.toLowerCase(),class:node.getAttribute('class')||'',kind,rect:{x:rect.x,y:rect.y,w:rect.width,h:rect.height},font:style.fontFamily,fontSize:style.fontSize,text:node.textContent.slice(0,2000),textNodes:[],savedClip:{value:node.style.getPropertyValue('clip-path'),priority:node.style.getPropertyPriority('clip-path')},keepVisible,removalRoot};
    if(kind==='media')e.media={status:node.querySelector('source')?.src||node.getAttribute('src')?'downloaded':'unsupported'};
    if(!keepVisible)for(const text of node.childNodes)if(text.nodeType===3&&text.textContent.trim())e.textNodes.push([text,text.textContent]);
    const master=!operation&&kind!=='media'&&(e.class||['a','li','article'].includes(e.tag))?[...s.elements.values()].find(other=>other.node!==node&&other.node.isConnected&&other.parent===dependency&&other.tag===e.tag&&other.class===e.class):null;
    e.master=master?.id||null;
    const op=operation||(master?'duplicate':({text:'type',image:'place',media:'place_media',line:'stroke'}[kind]||'draw'));
    const task={id,element:id,operation:op,duration:op==='type'?Math.min(3,.7+e.text.length/70):op==='remove'?.8:1,dependencies:[...new Set([dependency,master?.id].filter(Boolean))],dependencyPhases:dependency?{[dependency]:'frame'}:{},label:op+' '+e.tag,status:'pending',elapsed:0,scaffolded:false};
    s.elements.set(id,e);s.tasks.push(task);s.byId.set(id,task);s.model.elements.push(e);s.model.tasks.push(task);
    if(!keepVisible&&op!=='remove')node.setAttribute('data-sw-state','pending');
    s.boundsCache.clear();
  };
  creator.addTasks=root=>{
    const nodes=[...root.querySelectorAll('*')].filter(n=>!n.closest('svg,video,picture')||['SVG','VIDEO','PICTURE'].includes(n.tagName));
    let count=0;
    for(const node of nodes){
      if(['STYLE','SCRIPT','SOURCE','BR','DEFS','PATH','TITLE'].includes(node.tagName))continue;
      const r=node.getBoundingClientRect();if(r.width<2||r.height<2)continue;
      // Off-canvas accessibility links remain in the website, but are not
      // construction jobs: a vertical tour cannot reveal an x=-9999 skip link.
      if(r.right<=0||r.left>=s.width)continue;
      if(++count>500||s.tasks.length>=2500)break;
      creator.register(node);
    }
  };
  // Compare source trees, not animation-mutated live markup. Preserve matching
  // DOM nodes so unchanged media, inputs, and surrounding layout stay intact.
  creator.editBlock=(root,previous,html)=>{
    const old=s.doc.createElement('div'),next=s.doc.createElement('div');
    old.innerHTML=previous.html;next.innerHTML=html;
    const changed=new Map(),added=[];
    const sameShape=(a,b)=>a.nodeType===b.nodeType&&(a.nodeType!==1||a.tagName===b.tagName&&a.id===b.id);
    const morph=(live,before,after)=>{
      if(before.isEqualNode(after))return;
      if(before.nodeType===3){live.textContent=after.textContent;changed.set(live.parentElement,'type');return;}
      if(before.nodeType!==1&&before!==old)return;
      if(before.nodeType===1){
        for(const attr of before.attributes)if(!after.hasAttribute(attr.name))live.removeAttribute(attr.name);
        for(const attr of after.attributes)if(before.getAttribute(attr.name)!==attr.value)live.setAttribute(attr.name,attr.value);
        if([...before.attributes].some(a=>after.getAttribute(a.name)!==a.value)||[...after.attributes].some(a=>before.getAttribute(a.name)!==a.value))changed.set(live,'draw');
      }
      const a=[...before.childNodes],b=[...after.childNodes],current=[...live.childNodes];
      if(a.length===b.length&&a.every((n,i)=>sameShape(n,b[i]))){
        a.forEach((n,i)=>morph(current[i],n,b[i]));
      }else{
        // Structural edits replace only this changed subtree, never its section
        // siblings. The complete source remains authoritative for export.
        creator.retire(live);live.replaceChildren(...[...after.childNodes].map(n=>n.cloneNode(true)));
        changed.delete(live);added.push(live);
      }
    };
    morph(root,old,next);
    for(const node of added)creator.addTasks(node);
    for(const [node,operation] of changed){
      if(!node?.isConnected||added.some(parent=>parent.contains(node)))continue;
      creator.retire(node);creator.register(node,operation,operation!=='type');
    }
  };
  creator.flush=()=>{
    if(!creator.ready||!creator.pending.length)return;
    const command=creator.pending[0],root=command.id?creator.block(command.id):null;
    const blocked=root&&s.agents.some(a=>a.task&&root.contains(s.elements.get(a.task.element)?.node));
    if(blocked||command.action==='set_theme'&&s.agents.some(a=>a.task))return;
    creator.pending.shift();
    if(command.action==='set_theme'){
      s.doc.querySelector('#create-theme').textContent=base+creator.document.css+creator.document.blocks.map(b=>b.css).join('\n');
      for(const block of s.doc.querySelectorAll('[data-create-block]'))if(block.firstElementChild)creator.register(block.firstElementChild,'draw',true);
    }else if(command.action==='upsert_block'){
      if(root&&command.previous){creator.editBlock(root,command.previous,command.html);}
      else if(root){creator.retire(root);root.innerHTML=command.html;creator.addTasks(root);}
      else{const wrapper=s.doc.createElement('div');wrapper.dataset.createBlock=command.id;wrapper.style.display='contents';wrapper.innerHTML=command.html;const before=creator.block(command.before);s.doc.body.insertBefore(wrapper,before||null);}
      s.doc.querySelector('#create-theme').textContent=base+creator.document.css+creator.document.blocks.map(b=>b.css).join('\n');
      if(!root)creator.addTasks(creator.block(command.id));
      if(root&&command.previous&&command.previous.css!==command.css&&command.previous.html===command.html&&root.firstElementChild)creator.register(root.firstElementChild,'draw',true);
    }else if(command.action==='remove_block'&&root){
      creator.retire(root);const node=root.firstElementChild;
      if(node)creator.register(node,'remove',true,root);else root.remove();
    }
    s.scrollContainers=[s.doc.scrollingElement,...s.doc.querySelectorAll('[data-sw-id]')].filter(n=>n&&n.scrollHeight>n.clientHeight+30&&(/auto|scroll/.test(s.frame.contentWindow.getComputedStyle(n).overflowY)||n===s.doc.scrollingElement));
    s.camera.primary=s.doc.scrollingElement;s.camera.atEnd=false;s.finished=false;s.running=true;s.boundsCache.clear();
    if(creator.ended&&!creator.pending.length)s.liveOpen=false;
    creator.emit('creator-applied',{action:command.action,id:command.id||null});
  };
  creator.end=()=>{creator.ended=true;if(!creator.pending.length)s.liveOpen=false;};
  creator.speed=value=>s.setSpeed(value);
  creator.pause=()=>s.pause(!s.paused);
  creator.preview=enabled=>{
    creator.previewResolve?.();creator.previewResolve=null;
    creator.interactive=enabled;
    let frame=document.querySelector('#interactive');
    if(enabled){
      const fresh=document.createElement('iframe');fresh.id='interactive';fresh.title='Interactive generated website';fresh.setAttribute('sandbox','allow-scripts');
      frame.replaceWith(fresh);frame=fresh;
      s.pause(true);s.intro.style.display='none';s.canvas.style.display='none';s.frame.hidden=true;
      frame.hidden=false;frame.style.display='block';
      return new Promise(resolve=>{
        creator.previewResolve=resolve;
        const token=crypto.randomUUID();
        const loaded=async event=>{
          if(event.source!==frame.contentWindow||event.data?.type!=='creator-preview-loaded'||event.data.token!==token)return;
          removeEventListener('message',loaded);
          frame.getBoundingClientRect();
          await Promise.race([new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done))),new Promise(done=>setTimeout(done,80))]);
          if(creator.interactive){frame.contentWindow.postMessage({type:'select',value:creator.selecting},'*');creator.emit('creator-preview-ready');}
          creator.previewResolve=null;resolve();
        };
        addEventListener('message',loaded);
        frame.onload=null;frame.srcdoc=creator.source(creator.document,true,token);
      });
    }
    frame.onload=null;frame.hidden=true;frame.style.display='none';frame.srcdoc='';s.canvas.style.display='block';s.canvas.hidden=false;s.frame.hidden=false;if(s.running)s.pause(false);
    return Promise.resolve();
  };
  creator.select=value=>{
    creator.selecting=!!value;
    document.querySelector('#interactive').contentWindow.postMessage({type:'select',value:creator.selecting},'*');
    s.doc?.documentElement.classList.toggle('create-selecting',creator.selecting);
  };
  creator.installSelection=()=>{
    s.doc.addEventListener('click',event=>{
      if(!creator.selecting)return;
      event.preventDefault();event.stopImmediatePropagation();
      const node=event.target,block=node.closest('[data-create-block]');
      if(block)creator.emit('creator-selection',{block:block.dataset.createBlock,tag:node.tagName.toLowerCase(),text:(node.innerText||node.getAttribute('aria-label')||'').slice(0,180),id:node.id||''});
    },true);
    const style=s.doc.createElement('style');style.textContent='.create-selecting *{cursor:crosshair!important}.create-selecting *:hover{outline:1px solid #67bf9e!important;outline-offset:2px}';s.doc.head.append(style);
  };
  creator.diagnostics=()=>{
    if(!s.doc)return {};
    const nodes=[...s.doc.querySelectorAll('body *')],width=s.doc.documentElement.clientWidth;
    return {viewport:width,blocks:creator.document.blocks.map(b=>b.id),headings:s.doc.querySelectorAll('h1').length,
      horizontal_overflow:Math.max(0,s.doc.documentElement.scrollWidth-width),
      overflowing_elements:nodes.filter(n=>n.getBoundingClientRect().right>width+2).slice(0,8).map(n=>({tag:n.tagName,id:n.id,class:n.className?.toString().slice(0,80)})),
      missing_image_alt:[...s.doc.images].filter(n=>!n.hasAttribute('alt')).length,
      broken_anchors:[...s.doc.querySelectorAll('a[href^="#"]')].filter(n=>n.hash.length>1&&!s.doc.getElementById(decodeURIComponent(n.hash.slice(1)))).map(n=>n.hash).slice(0,12)};
  };
  creator.requestAudit=async(token)=>{
    const report={};
    for(const width of [1280,390]){
      const frame=document.createElement('iframe');frame.setAttribute('sandbox','allow-same-origin');
      frame.style.cssText=`position:fixed;left:-20000px;top:0;width:${width}px;height:844px;border:0;visibility:hidden`;
      try{
        const loaded=new Promise(resolve=>{frame.onload=resolve;});frame.srcdoc=creator.source(creator.document);document.body.append(frame);
        await Promise.race([loaded,new Promise(resolve=>setTimeout(resolve,1800))]);
        const doc=frame.contentDocument;
        if(!doc?.body){report[width]={unavailable:true};continue;}
        const port=doc.documentElement.clientWidth,nodes=[...doc.querySelectorAll('body *')];
        report[width]={viewport:port,horizontal_overflow:Math.max(0,doc.documentElement.scrollWidth-port),headings:doc.querySelectorAll('h1').length,
          overflowing_elements:nodes.filter(n=>n.getBoundingClientRect().right>port+2).slice(0,6).map(n=>({tag:n.tagName,id:n.id,class:String(n.className).slice(0,80)})),
          missing_image_alt:[...doc.images].filter(n=>!n.hasAttribute('alt')).length,
          broken_images:[...doc.images].filter(n=>n.naturalWidth===0).map(n=>(n.alt||'image').slice(0,80)).slice(0,6),
          broken_anchors:[...doc.querySelectorAll('a[href^="#"]')].filter(n=>{try{return n.hash.length>1&&!doc.getElementById(decodeURIComponent(n.hash.slice(1)));}catch(_){return true;}}).map(n=>n.hash).slice(0,8)};
      }catch(error){report[width]={unavailable:true};}
      finally{frame.remove();}
    }
    creator.emit('creator-audit',{report,token});
  };
  addEventListener('message',event=>{
    if(event.source!==document.querySelector('#interactive').contentWindow||!event.data||typeof event.data!=='object')return;
    if(event.data.type==='creator-selection'&&creator.selecting){
      const d=event.data;creator.emit('creator-selection',{block:String(d.block).slice(0,64),tag:String(d.tag).slice(0,20),text:String(d.text).slice(0,180),id:String(d.id).slice(0,100)});
    }
    if(event.data.type==='creator-runtime-error')creator.emit('creator-runtime-error',{message:String(event.data.message).slice(0,240)});
  });
  creator.load(empty).catch(error=>creator.emit('error',{message:error.message}));
})();

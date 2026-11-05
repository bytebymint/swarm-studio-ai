/* Independent rendered-DOM capture. Executed only in Qt's isolated ApplicationWorld. */
(() => {
  const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
  const unsafeURL = value => {try{const u=new URL(value,document.baseURI);return /^(javascript|vbscript|file):/i.test(value)||!!u.username||!!u.password||[...u.searchParams.keys()].some(k=>/token|password|secret|session|api.?key|credential|signature|authorization|jwt|policy|key-pair-id|^sig$/i.test(k));}catch(_){return true;}};
  window.StudioCapture = {
    state: {status: 'idle'}, cancelled: false,
    cancel() { this.cancelled = true; },
    async start(options = {}) {
      this.cancelled = false;
      this.state = {status: 'preparing'};
      const warnings = [], started = performance.now();
      const max = options.max_elements || 2500;
      const maxHeight = options.max_height || 30000;
      const deadline = started + (options.timeout || 25) * 1000;
      const scrollers = [document.scrollingElement || document.documentElement];
      for (const node of document.querySelectorAll('body *')) {
        if (scrollers.length >= 12) break;
        if (node.scrollHeight > node.clientHeight + 100 && node.clientHeight > 120 && /auto|scroll/.test(getComputedStyle(node).overflowY)) scrollers.push(node);
      }
      const positions = scrollers.map(node => [node, node.scrollTop, node.scrollLeft]);
      try {
        if (!document.body) throw new Error('The page has no document body.');
        if(unsafeURL(location.href))throw new Error('The current address contains a secret/session parameter. Open a public URL without session data.');
        if ([...document.querySelectorAll('input[type=password]')].some(input=>input.value) || document.querySelector('a[href*="logout"],a[href*="signout"],form[action*="logout"]')) throw new Error('This page appears to contain a signed-in session. Capture a public or local fixture without account contents.');
        if (options.lazy_load) {
          for (const node of scrollers) {
            const limit = Math.min(maxHeight, node.scrollHeight);
            for (let step = 1; step <= Math.min(16, Math.ceil(limit / Math.max(200, node.clientHeight))); step++) {
              if (this.cancelled || performance.now() > deadline) break;
              node.scrollTop = Math.min(limit, step * Math.max(200, node.clientHeight) * .85);
              await delay(55);
            }
          }
        }
        for (const [node, top, left] of positions) {node.scrollTop = top; node.scrollLeft = left;}
        await Promise.race([document.fonts.ready, delay(1200)]);
        await delay(100);
        if (this.cancelled) {this.state = {status:'cancelled'}; return;}
        this.state = {status:'inspecting'};
        const elements = [], styles = [], resources = new Set(), fonts = new Set(), sheets = [];
        const mediaAssets=[];
        const mediaURL = raw => {if(!raw)return null;try {const u=new URL(raw,document.baseURI);return /^https?:$/.test(u.protocol)&&!u.username&&!u.password&&!unsafeURL(u.href)?u.href:null;}catch(_){return null;}};
        const scrollState={window:{x:scrollX,y:scrollY},nodes:{}};
        let blockedSheets = false, count = 0, truncated = false;
        for (const sheet of document.styleSheets) {
          try { sheets.push({text: [...sheet.cssRules].map(rule => rule.cssText).join('\n'), base:sheet.href || document.baseURI}); }
          catch (_) { blockedSheets = true; if (sheet.href && !unsafeURL(sheet.href)) resources.add(sheet.href); }
        }
        if (blockedSheets) warnings.push('Some stylesheet rules were inaccessible. Computed-style fallback fixes appearance at the captured viewport; responsive and hover behavior may differ.');
        const cloneDoc = document.implementation.createHTMLDocument(document.title || 'Reconstruction');
        cloneDoc.documentElement.lang = document.documentElement.lang || 'en';
        const viewport = cloneDoc.createElement('meta'); viewport.name='viewport'; viewport.content='width=device-width, initial-scale=1'; cloneDoc.head.append(viewport);
        const attributes = /^(id|class|role|lang|dir|title|alt|width|height|viewBox|d|fill|stroke|stroke-width|stroke-linecap|stroke-linejoin|xmlns|x|y|x1|x2|y1|y2|cx|cy|r|rx|ry|points|transform|preserveAspectRatio|colspan|rowspan|scope|span|type|placeholder|disabled|multiple|open|controls|loop|muted|preload|loading|for|tabindex|aria-[\w-]+)$/i;
        const drop = new Set(['script','noscript','template','link','meta','base','style','object','embed']);
        const walk = (source, parentId = null, svg = false) => {
          if (this.cancelled) throw new Error('Capture cancelled.');
          if (++count > max * 5 || performance.now() > deadline) {truncated = true; return null;}
          if (source.nodeType === 3) return cloneDoc.createTextNode(source.textContent);
          if (source.nodeType !== 1 || drop.has(source.localName)) return null;
          const tag = source.localName, cs = getComputedStyle(source), rect = source.getBoundingClientRect();
          const isSVG = svg || tag === 'svg';
          const id = 's' + count;
          let dest, media;
          if (tag === 'iframe') {
            dest = cloneDoc.createElement('div'); dest.textContent = 'Embedded frame not captured';
            dest.setAttribute('role','img'); dest.setAttribute('aria-label','Unsupported embedded frame');
            warnings.push(`Frame excluded at ${Math.round(rect.x)}, ${Math.round(rect.y)}: browser isolation.`);
            try {
              const url=new URL(source.src,document.baseURI),match=url.pathname.match(/^\/embed\/([a-zA-Z0-9_-]{11})$/);
              if(['https:','http:'].includes(url.protocol)&&!url.username&&!url.password&&['www.youtube.com','youtube.com','www.youtube-nocookie.com','youtube-nocookie.com'].includes(url.hostname)&&match){
                const videoId=match[1],poster=`https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
                media={sources:[],currentSrc:null,provider:'youtube',hosting:'third-party',videoId,embedUrl:`https://www.youtube.com/embed/${videoId}`,externalUrl:`https://www.youtube.com/watch?v=${videoId}`,poster,status:'embedded',autoplay:url.searchParams.get('autoplay')==='1',loop:url.searchParams.get('loop')==='1',muted:true,controls:false,paused:true,currentTime:0,playbackRate:1,width:rect.width,height:rect.height,aspectRatio:cs.aspectRatio};
                mediaAssets.push({id,kind:'media',media,rect:{x:rect.x+scrollX,y:rect.y+scrollY,w:rect.width,h:rect.height}});
                dest.setAttribute('poster',poster);resources.add(poster);
                warnings.push(`YouTube video ${id}: embedded player excluded; thumbnail fallback only, not a downloaded video.`);
              }
            }catch(_){ /* Unknown embeds retain the existing isolated placeholder. */ }
          } else if (tag === 'canvas') {
            dest = cloneDoc.createElement('img'); dest.alt = 'Captured canvas image fallback';
            try {dest.src = source.toDataURL('image/png'); warnings.push('Canvas captured as a raster image fallback, without live behavior.');}
            catch (_) {warnings.push('Tainted or unsupported canvas could not be captured.');}
          } else dest = isSVG ? cloneDoc.createElementNS('http://www.w3.org/2000/svg', tag) : cloneDoc.createElement(tag.includes('-') ? 'div' : tag);
          for (const attr of source.attributes) {
            if (attributes.test(attr.name) && !['value','checked','selected'].includes(attr.name)) dest.setAttribute(attr.name, attr.value);
          }
          dest.setAttribute('data-sw-id', id);
          if(source.scrollHeight>source.clientHeight+10||source.scrollWidth>source.clientWidth+10)scrollState.nodes[id]={top:source.scrollTop,left:source.scrollLeft};
          if (source.hasAttribute('style')) dest.setAttribute('style', source.getAttribute('style'));
          if (['input','textarea'].includes(tag)) {dest.removeAttribute('value'); dest.removeAttribute('name'); dest.removeAttribute('autocomplete');}
          if (tag === 'form') {dest.setAttribute('onsubmit','return false'); dest.removeAttribute('action'); warnings.push('Form values and remote submission excluded.');}
          if (tag === 'a') {
            const raw = source.getAttribute('href') || '';
            if (raw.startsWith('#')) dest.setAttribute('href',raw);
            else if (!unsafeURL(source.href) && /^https?:/.test(source.href)) {dest.setAttribute('href',source.href); dest.setAttribute('rel','noreferrer noopener'); dest.setAttribute('target','_blank');}
          }
          for (const attr of ['src', 'poster']) {
            if(tag==='video'&&attr==='src')continue; // Media policy below decides which candidates are safe.
            let value = tag === 'img' && attr === 'src' ? source.currentSrc || source.src : source[attr];
            if (tag === 'iframe' || tag === 'canvas' || !value || unsafeURL(value)) continue;
            if (/^(https?:|data:image\/|blob:)/i.test(value)) {dest.setAttribute(attr,value); if (/^https?:/.test(value)) resources.add(value);}
          }
          if (tag === 'img') {dest.removeAttribute('srcset'); dest.setAttribute('loading','eager');}
          if (tag === 'video') {
            const candidates=[source.currentSrc,source.getAttribute('src'),source.getAttribute('data-src'),source.getAttribute('data-lazy-src'),...Array.from(source.querySelectorAll('source')).flatMap(n=>[n.src,n.getAttribute('data-src')])].filter(Boolean);
            const sources=[...new Set(candidates.map(mediaURL).filter(Boolean))];
            const encrypted=!!source.mediaKeys;
            media={sources:encrypted?[]:sources,currentSrc:encrypted?null:mediaURL(source.currentSrc),poster:mediaURL(source.poster),autoplay:source.autoplay,muted:source.muted,loop:source.loop,controls:source.controls,preload:source.preload,playsinline:source.playsInline,currentTime:Number.isFinite(source.currentTime)?source.currentTime:0,paused:source.paused,playbackRate:source.playbackRate,width:source.videoWidth,height:source.videoHeight,aspectRatio:cs.aspectRatio,status:encrypted?'protected':sources.length?'discovered':'unsupported'};
            media.provider='html5';media.hosting=sources.length?(new URL(sources[0]).origin===location.origin?'same-origin':'third-party'):'unknown';
            media.sourceUrls=[...media.sources];
            mediaAssets.push({id,kind:'media',media});
            dest.removeAttribute('src');
            if(!encrypted&&sources.length){dest.src=sources[0];for(const url of sources)resources.add(url);}
            for(const key of ['autoplay','loop','controls','playsinline'])if(media[key])dest.setAttribute(key,'');else dest.removeAttribute(key);
            if(media.muted)dest.setAttribute('muted','');else dest.removeAttribute('muted');
            if(!sources.length||encrypted)warnings.push(`Video ${id}: unsupported or protected source; only an available poster can be preserved.`);
          }
          if (tag === 'svg') dest.removeAttribute('style');
          let computed = '';
          for (const property of cs) {
            const value = cs.getPropertyValue(property);
            if (property.startsWith('--') || !value) continue;
            computed += property + ':' + value + ';';
            for (const match of value.matchAll(/url\(["']?([^"')]+)["']?\)/g)) {
              try { const url = new URL(match[1],document.baseURI).href; if (/^https?:/.test(url) && !unsafeURL(url)) resources.add(url); } catch (_) {}
            }
          }
          if (blockedSheets || source.shadowRoot || tag.includes('-') || tag==='iframe'&&media) styles.push(`[data-sw-id="${id}"]{${computed}}`);
          const visible = cs.display !== 'none' && cs.visibility !== 'hidden' && rect.width > .5 && rect.height > .5;
          const directText = [...source.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('').trim();
          const paintable = !svg && visible && elements.length < max && rect.top + scrollY < maxHeight;
          let nextParent = parentId;
          if (paintable) {
            let kind = media?'media':['img','svg','canvas','iframe'].includes(tag) ? 'image' : tag === 'hr' ? 'line' : directText ? 'text' : 'container';
            const text = ['input','textarea','select'].includes(tag) ? '' : directText;
            elements.push({id, parent:parentId, tag, class:source.className?.baseVal ?? String(source.className || ''), kind, text,
              rect:{x:rect.x+scrollX, y:rect.y+scrollY, w:rect.width, h:rect.height},
              font:cs.fontFamily, fontSize:cs.fontSize, color:cs.color, background:cs.backgroundColor, position:cs.position,
              scrollable:source.scrollHeight > source.clientHeight + 10, order:elements.length,
              originalBox:{x:rect.x,y:rect.y,w:rect.width,h:rect.height},...(media?{media}: {})});
            nextParent = id; fonts.add(cs.fontFamily);
          }
          if (!['textarea','input','canvas','iframe','video'].includes(tag)) {
            const children = source.shadowRoot ? source.shadowRoot.childNodes : source.childNodes;
            if (source.shadowRoot) warnings.push('Open shadow tree flattened; component scripts are excluded.');
            for (const child of children) {const copy=walk(child,nextParent,isSVG); if (copy) dest.append(copy);}
          }
          return dest;
        };
        const body = walk(document.body);
        if (!body) throw new Error('No reconstructable document was found.');
        cloneDoc.body.replaceWith(body);
        // Preserve root style rules targeting html, including theme classes.
        cloneDoc.documentElement.className = document.documentElement.className;
        if (document.documentElement.style.cssText) cloneDoc.documentElement.style.cssText = document.documentElement.style.cssText;
        if (truncated || elements.length >= max) warnings.push('Capture reached a configured element, height or time limit. Document may be partial.');
        if (document.querySelector('input[type=password]')) warnings.push('Password fields were cleared. No browser session or form values were copied.');
        this.state = {status:'complete', result:{schema:1, title:document.title, url:location.href,
          html:'<!doctype html>\n'+cloneDoc.documentElement.outerHTML, sheets, computedCSS:styles.join('\n'), stylesheets:[...document.styleSheets].map(s=>s.href).filter(Boolean),
          elements, media:mediaAssets, resources:[...resources], fonts:[...fonts], warnings:[...new Set(warnings)],scrollState,
          links:[...document.querySelectorAll('a[href]')].map(a=>a.href).filter(url=>url.startsWith(location.origin+'/')&&!unsafeURL(url)),
          viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},
          height:Math.min(maxHeight,Math.max(document.documentElement.scrollHeight,innerHeight)),
          duration:Math.round(performance.now()-started)}};
      } catch(error) {this.state = {status:this.cancelled ? 'cancelled':'error', error:error.message};}
      finally {for (const [node,top,left] of positions) {node.scrollTop=top;node.scrollLeft=left;}}
    }
  };
})();

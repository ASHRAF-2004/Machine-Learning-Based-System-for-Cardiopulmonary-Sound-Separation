// Isolated production-optimized DEMO build; never changes the live preview or deployment.
import {build} from 'vite';
import {chromium} from 'playwright-core';
import {createServer} from 'node:http';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..'),out=path.join(root,'evidence/winter-glass/quality');
const built=path.join(root,'node_modules/.cache/winter-quality');
await mkdir(out,{recursive:true});process.env.VITE_ENABLE_DEMO='true';
await build({root,mode:'production',build:{outDir:built,copyPublicDir:false,emptyOutDir:true},logLevel:'warn'});
const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.json':'application/json','.woff2':'font/woff2','.gz':'application/octet-stream'};
const server=createServer(async(req,res)=>{try{
 const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
 if(pathname.includes('..')){res.writeHead(400);res.end();return;}
 const rel=pathname.replace(/^\//,'');let file;
 for(const candidate of [path.join(built,rel),path.join(root,'public',rel)]){try{const bytes=await readFile(candidate);file={candidate,bytes};break;}catch{}}
 if(!file&&!path.extname(pathname))file={candidate:'index.html',bytes:await readFile(path.join(built,'index.html'))};
 if(!file){res.writeHead(404);res.end();return;}
 res.writeHead(200,{'Content-Type':types[path.extname(file.candidate)]||'application/octet-stream','Cache-Control':'no-store'});res.end(file.bytes);
}catch{res.writeHead(500);res.end();}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const report={date:new Date().toISOString(),browser:await browser.version(),method:'One-shot fresh-context localhost production-optimized DEMO build. Server sends identity encoding, no throttling; server/OS cache not flushed. No field-device or hardware-GPU claim. Tests do not alter the live dev preview.',samples:[],contrast:[]};
try{
 for(const sample of [{name:'dashboard-desktop',route:'/app/dashboard',uid:'USR-1001',width:1440,height:1000},{name:'ensemble-desktop',route:'/app/admin/ensemble',uid:'USR-3001',width:1440,height:1000},{name:'review-mobile',route:'/app/reviews/ASN-401',uid:'USR-2001',width:390,height:844},{name:'login-desktop',route:'/login',width:1440,height:1000}]){
  const context=await browser.newContext({viewport:{width:sample.width,height:sample.height},deviceScaleFactor:1});
  await context.addInitScript(uid=>{if(uid)sessionStorage.setItem('stethofuse-demo-persona',uid);window.__qualityCLS=0;window.__qualityLCP=0;
   new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.__qualityCLS+=e.value;}).observe({type:'layout-shift',buffered:true});
   new PerformanceObserver(l=>{for(const e of l.getEntries())window.__qualityLCP=e.startTime;}).observe({type:'largest-contentful-paint',buffered:true});
  },sample.uid);
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
  await page.goto(base+sample.route,{waitUntil:'networkidle'});await page.locator('h1').first().waitFor();await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(250);
  const resources=await page.evaluate(()=>performance.getEntriesByType('resource').map(r=>({path:new URL(r.name).pathname,encoded:r.encodedBodySize,decoded:r.decodedBodySize,transfer:r.transferSize,duration:r.duration})));
  const timings=await page.evaluate(()=>({fcp:performance.getEntriesByName('first-contentful-paint')[0]?.startTime,lcp:window.__qualityLCP,cls:window.__qualityCLS,viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},documentWidth:document.documentElement.scrollWidth,canvas:[...document.querySelectorAll('canvas')].map(c=>({width:c.width,height:c.height}))}));
  // Scroll the actual glass-covered document; report frame intervals, not an FPS guarantee.
  const intervals=await page.evaluate(()=>new Promise(resolve=>{let previous=0;const values=[];let frame=0;function tick(t){if(previous)values.push(t-previous);previous=t;window.scrollTo(0,(document.documentElement.scrollHeight-innerHeight)*(1-Math.cos(frame/180*Math.PI*2))/2);if(++frame<=180)requestAnimationFrame(tick);else{window.scrollTo(0,0);resolve(values);}}requestAnimationFrame(tick);}));
  intervals.sort((a,b)=>a-b);
  await page.screenshot({path:path.join(out,sample.name+'.png'),fullPage:true});
  report.samples.push({...sample,...timings,errors,resources,encodedBodyBytes:resources.reduce((n,r)=>n+r.encoded,0),transferBytes:resources.reduce((n,r)=>n+r.transfer,0),scrollFrameMs:{median:intervals[Math.floor(intervals.length*.5)],p95:intervals[Math.floor(intervals.length*.95)],max:Math.max(...intervals)}});
  // Observe real composited background with glyph colour temporarily hidden.
  // Range rectangles restrict the check to text, not whole cards or button rims.
  const text=await page.evaluate(()=>{
   const selectors=['h1','.eyebrow','.page-description','.breadcrumbs','.demo-banner','.panel-heading p','.field>span','.field>small','.timestamp-note code','.timestamp-note p','.workspace-footer','.auth-form>.muted','.auth-demo-note','.auth-links','.auth-meta','.form-divider','.auth-foot','.button-primary'];
   return selectors.flatMap(selector=>[...document.querySelectorAll(selector)].flatMap(el=>{
    if(el.closest('[disabled]'))return [];const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT),rows=[];let node;
    while(node=walker.nextNode()){if(!node.textContent.trim())continue;const css=getComputedStyle(node.parentElement),r=document.createRange();r.selectNodeContents(node);for(const b of r.getClientRects()){if(b.width<1||b.height<1||b.bottom<=0||b.top>=innerHeight)continue;rows.push({selector,text:node.textContent.trim().slice(0,80),color:css.color,fontSize:parseFloat(css.fontSize),fontWeight:parseInt(css.fontWeight)||400,rect:{x:b.x,y:b.y,width:b.width,height:b.height}});}}
    return rows;
   }));
  });
  await page.addStyleTag({content:'*,*::before,*::after{color:transparent!important;text-shadow:none!important;-webkit-text-fill-color:transparent!important}'});
  await page.screenshot({path:path.join(out,sample.name+'-background.png')});
  report.contrast.push({name:sample.name,text});
  await context.close();
 }
 await writeFile(path.join(out,'metrics.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify(report.samples.map(({name,fcp,lcp,cls,encodedBodyBytes,transferBytes,scrollFrameMs,errors})=>({name,fcp,lcp,cls,encodedBodyBytes,transferBytes,scrollFrameMs,errors})),null,2));
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}

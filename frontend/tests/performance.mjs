import {chromium} from 'playwright-core';
import {mkdir,readFile,readdir,writeFile} from 'node:fs/promises';
import {gzipSync} from 'node:zlib';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const base=process.env.PERFORMANCE_URL||'http://127.0.0.1:4181';
const output=path.join(root,'evidence/performance');
await mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const results={testedAt:new Date().toISOString(),base,browser:await browser.version(),method:{headless:true,cache:'New isolated browser context per sample; browser HTTP cache disabled through CDP. Operating-system and server caches are not flushed.',sampleCount:1,fieldData:false,hardwareGpuValidated:false,observation:'Navigation until fonts, hero images and network are ready, then one additional idle second. No mouse movement or animation interaction during initial-load measurement.',bytes:'Resource Timing encodedBodySize is the encoded response body; decodedBodySize is decompressed response-body bytes, NOT decoded image or application memory. transferSize includes browser-reported protocol/header overhead. Gzip figures are separate level-9 build-file estimates, not what this preview server transferred.',timing:'Single localhost lab observations, not production field percentiles or Lighthouse scores.'},samples:[],productionBoundary:[],buildFiles:[]};
const category=name=>/\.(?:woff2?|ttf|otf)(?:\?|$)/i.test(name)?'fonts':/\.(?:webp|avif|png|jpe?g|svg|gif|ico)(?:\?|$)/i.test(name)?'images':/\.js(?:\?|$)/.test(name)?'javascript':/\.css(?:\?|$)/.test(name)?'stylesheets':'other';
const configs=[
 {name:'desktop-localhost',viewport:{width:1440,height:900},deviceScaleFactor:1,isMobile:false,hasTouch:false},
 {name:'mobile-emulation-localhost',viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true},
 {name:'desktop-throttled-emulation',viewport:{width:1440,height:900},deviceScaleFactor:1,isMobile:false,hasTouch:false,throttle:{latencyMs:150,downloadBitsPerSecond:1600000,uploadBitsPerSecond:750000,cpuSlowdown:4}}
];
try{
 for(const config of configs){
  console.log(`MEASURE ${config.name}`);
  const {name,throttle,...contextOptions}=config;
  const context=await browser.newContext(contextOptions);
  const page=await context.newPage(),cdp=await context.newCDPSession(page);
  const errors=[],consoleErrors=[],failedRequests=[],responses=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')consoleErrors.push(message.text());});
  page.on('requestfailed',request=>failedRequests.push({url:request.url(),failure:request.failure()}));
  await cdp.send('Network.enable');await cdp.send('Network.setCacheDisabled',{cacheDisabled:true});await cdp.send('Performance.enable');
  cdp.on('Network.responseReceived',event=>responses.push({url:event.response.url,status:event.response.status,mimeType:event.response.mimeType,contentEncoding:event.response.headers['Content-Encoding']||event.response.headers['content-encoding']||null,fromDiskCache:event.response.fromDiskCache||false,fromServiceWorker:event.response.fromServiceWorker||false}));
  if(throttle){await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:throttle.latencyMs,downloadThroughput:throttle.downloadBitsPerSecond/8,uploadThroughput:throttle.uploadBitsPerSecond/8,connectionType:'cellular3g'});await cdp.send('Emulation.setCPUThrottlingRate',{rate:throttle.cpuSlowdown});}
  await page.addInitScript(()=>{
   window.__stethofusePerf={lcp:null,layoutShifts:[],longTasks:[],supported:PerformanceObserver.supportedEntryTypes};
   if(PerformanceObserver.supportedEntryTypes.includes('largest-contentful-paint'))new PerformanceObserver(list=>{for(const entry of list.getEntries())window.__stethofusePerf.lcp={time:entry.startTime,size:entry.size,url:entry.url||null,element:entry.element?`${entry.element.tagName.toLowerCase()}.${String(entry.element.className||'').replaceAll(' ','.')}`:null};}).observe({type:'largest-contentful-paint',buffered:true});
   if(PerformanceObserver.supportedEntryTypes.includes('layout-shift'))new PerformanceObserver(list=>{for(const entry of list.getEntries())if(!entry.hadRecentInput)window.__stethofusePerf.layoutShifts.push({time:entry.startTime,value:entry.value,sources:entry.sources?.map(source=>({element:source.node?.nodeName||null,previousRect:source.previousRect?.toJSON?.(),currentRect:source.currentRect?.toJSON?.()}))||[]});}).observe({type:'layout-shift',buffered:true});
   if(PerformanceObserver.supportedEntryTypes.includes('longtask'))new PerformanceObserver(list=>{for(const entry of list.getEntries())window.__stethofusePerf.longTasks.push({start:entry.startTime,duration:entry.duration});}).observe({type:'longtask',buffered:true});
  });
  await page.goto(base+'/',{waitUntil:'networkidle',timeout:60000});
  await page.locator('#welcome-title').waitFor();
  await page.evaluate(()=>document.fonts.ready);
  await page.waitForFunction(()=>[...document.querySelectorAll('.public-nav img,.owl-art img')].every(img=>img.complete&&img.naturalWidth>0));
  await page.waitForTimeout(1000);
  const data=await page.evaluate(()=>{
   const nav=performance.getEntriesByType('navigation')[0],paint=performance.getEntriesByType('paint'),observed=window.__stethofusePerf;
   let cls=0,windowValue=0,windowStart=0,lastShift=0;
   for(const shift of observed.layoutShifts){if(shift.time-lastShift>1000||shift.time-windowStart>5000){windowValue=0;windowStart=shift.time;}windowValue+=shift.value;lastShift=shift.time;cls=Math.max(cls,windowValue);}
   const resourceFields=r=>({url:r.name,initiatorType:r.initiatorType||'navigation',startTime:r.startTime,duration:r.duration,responseStart:r.responseStart,responseEnd:r.responseEnd,transferSize:r.transferSize,encodedBodySize:r.encodedBodySize,decodedBodySize:r.decodedBodySize,protocol:r.nextHopProtocol});
   return {viewport:{width:innerWidth,height:innerHeight},documentWidth:document.documentElement.scrollWidth,dpr:devicePixelRatio,finePointer:matchMedia('(pointer:fine)').matches,coarsePointer:matchMedia('(pointer:coarse)').matches,reducedMotion:matchMedia('(prefers-reduced-motion:reduce)').matches,userAgent:navigator.userAgent,measuredUntilMs:performance.now(),navigation:resourceFields(nav),timings:{ttfbMs:nav.responseStart,domContentLoadedMs:nav.domContentLoadedEventEnd,loadEventEndMs:nav.loadEventEnd,firstPaintMs:paint.find(e=>e.name==='first-paint')?.startTime??null,firstContentfulPaintMs:paint.find(e=>e.name==='first-contentful-paint')?.startTime??null,largestContentfulPaint:observed.lcp,cls,observedLongTaskBlockingMs:observed.longTasks.reduce((n,e)=>n+Math.max(0,e.duration-50),0),longTasks:observed.longTasks,layoutShifts:observed.layoutShifts,observerSupport:observed.supported},resources:performance.getEntriesByType('resource').map(resourceFields),images:[...document.images].map(img=>({src:img.currentSrc,naturalWidth:img.naturalWidth,naturalHeight:img.naturalHeight,displayWidth:img.getBoundingClientRect().width,displayHeight:img.getBoundingClientRect().height})),canvas:[...document.querySelectorAll('canvas')].map(c=>({drawingWidth:c.width,drawingHeight:c.height,displayWidth:c.getBoundingClientRect().width,displayHeight:c.getBoundingClientRect().height})),demoPersonaButtons:document.querySelectorAll('.persona-option').length,storage:{localKeys:Object.keys(localStorage),sessionKeys:Object.keys(sessionStorage)}};
  });
  const all=[{...data.navigation,category:'document'},...data.resources.map(resource=>({...resource,category:category(resource.url)}))];
  const totals={};for(const resource of all){const sum=totals[resource.category]||(totals[resource.category]={requests:0,transferSize:0,encodedBodySize:0,decodedBodySize:0});sum.requests++;for(const key of ['transferSize','encodedBodySize','decodedBodySize'])sum[key]+=resource[key];}
  const initialFrames=responses.filter(r=>/\/assets\/owl\/(?:frames|body|transition)/.test(r.url));
  const privateChunks=responses.filter(r=>/\/(?:AccountPages|WorkspacePages|AudioWorkbench)-[^/]+\.js/.test(r.url));
  const snapshot=await cdp.send('Performance.getMetrics');
  const metrics=Object.fromEntries(snapshot.metrics.map(m=>[m.name,m.value]));
  const httpErrors=responses.filter(response=>response.status>=400);
  const checks={heroLoaded:data.images.some(img=>img.src.includes('owl-poster')&&img.naturalWidth>0),noInitialAnimationFrames:initialFrames.length===0,noPrivateWorkspaceChunks:privateChunks.length===0,noPersonaButtons:data.demoPersonaButtons===0,noStorageWritten:data.storage.localKeys.length===0&&data.storage.sessionKeys.length===0,noHorizontalOverflow:data.documentWidth<=data.viewport.width+1,noRuntimeErrors:errors.length===0,noConsoleErrors:consoleErrors.length===0,noHttpErrors:httpErrors.length===0,noFailedRequests:failedRequests.length===0,initialJavaScriptUnder250KB:(totals.javascript?.encodedBodySize||0)<250000,initialImagesUnder500KB:(totals.images?.encodedBodySize||0)<500000};
  const sample={name,emulation:{...contextOptions,throttle:throttle||null,realDevice:false},...data,totals,totalEncodedBodyBytes:all.reduce((n,r)=>n+r.encodedBodySize,0),totalTransferBytes:all.reduce((n,r)=>n+r.transferSize,0),responseEncodings:[...new Set(responses.map(r=>r.contentEncoding||'identity'))],responses,initialFrames,privateChunks,checks,errors,consoleErrors,httpErrors,failedRequests,jsHeap:{usedBytes:metrics.JSHeapUsedSize,totalBytes:metrics.JSHeapTotalSize,note:'CDP JavaScript heap snapshot, not total browser, decoded image, canvas or GPU memory.'}};
  await page.screenshot({path:path.join(output,`${name}.png`)});
  results.samples.push(sample);console.log(JSON.stringify({name,timings:sample.timings,totalEncodedBodyBytes:sample.totalEncodedBodyBytes,checks},null,2));
  await context.close();
 }
 const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage();
 const check=async(name,fn)=>{try{await fn();results.productionBoundary.push({name,status:'PASS'});console.log(`PASS ${name}`);}catch(error){results.productionBoundary.push({name,status:'FAIL',error:error.message});console.log(`FAIL ${name}: ${error.message}`);}};
 await check('Normal production login has no persona selector and states authentication is unconfigured',async()=>{await page.goto(base+'/login',{waitUntil:'networkidle'});await page.getByRole('heading',{name:'Welcome back.',exact:true}).waitFor();await page.getByText('Authentication is not configured.',{exact:true}).waitFor();assert.equal(await page.locator('.persona-option').count(),0);assert.equal(await page.locator('#demo-personas').count(),0);await page.screenshot({path:path.join(output,'production-login.png')});});
 await check('Direct /app route redirects to login rather than granting fixture access',async()=>{await page.goto(base+'/app/dashboard',{waitUntil:'networkidle'});await page.waitForURL(/\/login\?/);assert.equal(new URL(page.url()).searchParams.get('returnTo'),'/app/dashboard');});
 await check('Forged demo storage does not enable a production authentication bypass',async()=>{await page.evaluate(()=>{sessionStorage.setItem('stethofuse-demo-persona','USR-3001');localStorage.setItem('stethofuse-demo-v1',JSON.stringify({users:[{id:'USR-3001',role:'admin',status:'active',verified:true}],recordings:[],preferences:{}}));});await page.goto(base+'/app/admin',{waitUntil:'networkidle'});await page.waitForURL(/\/login\?/);assert.equal(await page.getByRole('heading',{name:'Operational overview',exact:true}).count(),0);await page.evaluate(()=>{sessionStorage.clear();localStorage.clear();});});
 await check('Production sign-in remains an honest failure and sends no credentials',async()=>{const outbound=[];page.on('request',r=>{if(!['GET','HEAD'].includes(r.method()))outbound.push({method:r.method(),url:r.url()});});await page.goto(base+'/login',{waitUntil:'networkidle'});await page.getByLabel('Email address',{exact:true}).fill('fictional-performance@example.test');await page.getByLabel('Password',{exact:true}).fill('Not-a-real-password-482');await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.getByText(/Sign-in is unavailable because the identity provider has not been configured/).waitFor();assert.equal(await page.getByLabel('Password',{exact:true}).inputValue(),'');assert.equal(outbound.length,0);assert.equal(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}).includes('Not-a-real-password-482')),false);});
 await context.close();
 const assetDir=path.join(root,'dist/assets');
 for(const file of (await readdir(assetDir)).filter(name=>/\.(?:js|css)$/.test(name)).sort()){const buffer=await readFile(path.join(assetDir,file));results.buildFiles.push({file,rawBytes:buffer.byteLength,gzipLevel9Bytes:gzipSync(buffer,{level:9}).byteLength,publicInitialRequested:results.samples[0].resources.some(r=>r.url.endsWith('/'+file))});}
 results.publicInitialBuildGzipBytes=results.buildFiles.filter(file=>file.publicInitialRequested).reduce((n,file)=>n+file.gzipLevel9Bytes,0);
 results.status=results.samples.every(s=>Object.values(s.checks).every(Boolean))&&results.productionBoundary.every(c=>c.status==='PASS')?'PASS':'FAIL';
 await writeFile(path.join(output,'results.json'),JSON.stringify(results,null,2));
 const kb=bytes=>(bytes/1024).toFixed(1),ms=value=>value===null||value===undefined?'Not observable':`${Math.round(value)} ms`;
 const lines=[
 '# Frontend performance observations','',`Measured ${results.testedAt} with Chrome ${results.browser}, headless on Ubuntu, against ${base}.`,'','## Method','',
 'Each sample uses a fresh isolated browser context and disables the browser HTTP cache. Server and operating-system caches are not flushed. These are one-shot local lab observations, not production field percentiles, a Lighthouse score, or real-device measurements. The machine is shared with ongoing development work; host load is not controlled. No pointer movement was sent during the initial-load window. Fonts and hero images were ready before a final one-second idle observation.','',
 'The desktop sample uses 1440 × 900 at DPR 1. The mobile sample emulates 390 × 844 at DPR 2 with touch/coarse-pointer behavior. The throttled desktop uses CDP network emulation: 150 ms latency, 1.6 Mbps down, 0.75 Mbps up, plus 4× CPU slowdown. This does not model every property of a slow phone or remote deployment.','',
 'The web-perf skill’s Chrome DevTools MCP was unavailable. The existing Playwright/Chrome connection and CDP supplied Resource Timing, paint observers, layout shifts and heap snapshots without installing tools. No Core Web Vitals rating is inferred from these isolated samples.','',
 '| Sample | FCP | LCP | CLS | Encoded response bodies | Browser-reported transfer |','|---|---:|---:|---:|---:|---:|',
 ...results.samples.map(s=>`| ${s.name} | ${ms(s.timings.firstContentfulPaintMs)} | ${ms(s.timings.largestContentfulPaint?.time)} | ${s.timings.cls.toFixed(4)} | ${kb(s.totalEncodedBodyBytes)} KiB | ${kb(s.totalTransferBytes)} KiB |`),'',
 '## Initial resources by type','',
 '| Sample | Resource type | Requests | Encoded body | Decoded response body |','|---|---|---:|---:|---:|',
 ...results.samples.flatMap(s=>Object.entries(s.totals).map(([type,t])=>`| ${s.name} | ${type} | ${t.requests} | ${kb(t.encodedBodySize)} KiB | ${kb(t.decodedBodySize)} KiB |`)),'',
 '**Encoded body bytes** are the actual encoded response bodies reported by Chrome. **Decoded body bytes** are response-body decompression sizes, not decoded texture/RGBA, GPU, canvas or total application memory. The preview server used the content encodings listed in `evidence/performance/results.json`; do not substitute gzip estimates for these observed transfers. Resource Timing transfer sizes include browser-reported overhead.','',
 '## Route splitting and gzip comparison','',
 'The following gzip values are measured by compressing build artifacts locally at gzip level 9. They are potential delivery sizes if a server enables that compression; this task did not change deployment or server compression settings.','',
 '| Build file | Raw | Gzip level 9 | Requested by initial public page |','|---|---:|---:|---|',
 ...results.buildFiles.map(f=>`| ${f.file} | ${kb(f.rawBytes)} KiB | ${kb(f.gzipLevel9Bytes)} KiB | ${f.publicInitialRequested?'Yes':'No'} |`),'',
 `Initial requested JavaScript + CSS gzip-level-9 total: **${kb(results.publicInitialBuildGzipBytes)} KiB**. Fonts and decorative images are accounted for separately above. Private workspace, administration/account and audio-workbench chunks must remain absent from public initial requests. The complete file list, actual requests and errors are preserved in the JSON evidence.`, '',
 '## Checks','',
 ...results.samples.flatMap(s=>Object.entries(s.checks).map(([name,passed])=>`- ${passed?'PASS':'FAIL'}: ${s.name} · ${name}.`)),
 ...results.productionBoundary.map(c=>`- ${c.status}: ${c.name}${c.error?` — ${c.error}`:''}.`),'',
 'Initial-load frame fetching is checked separately from pointer-driven animation. The interaction renderer may load assets after input; that is outside this initial-load measurement. Canvas drawing dimensions, displayed dimensions, DPR, selected poster sources, and per-resource timings are in the JSON. Image `naturalWidth`/`naturalHeight` are DOM density-corrected values when `srcset` is used, not necessarily raw file dimensions. JavaScript heap snapshots are observable but are not total browser or decoded-image memory.','',
 '## Reproduce','',
 '```bash','cd /home/ashraf/Documents/StethoFuse/implementation/frontend','npm run build','npm run preview -- --port 4181','# In another terminal:','node tests/performance.mjs','```','',
 'Do not set `VITE_ENABLE_DEMO=true` for this production-boundary check. The development-only personas remain available through `npm run dev` on port 4180. Live authentication remains unconfigured and requires the documented Firebase adapter/backend integration.','',
 'Evidence: `evidence/performance/results.json`, desktop/mobile/throttled screenshots and `production-login.png`. No HTML, stylesheet, assets, renderer or deployment configuration was modified by this performance task.','',
 `Overall automated measurement/check status: **${results.status}**. This is not a claim that the complete app or owl has production field-performance approval.`,''
 ];
 await writeFile(path.join(root,'PERFORMANCE.md'),lines.join('\n'));
 console.log(`PERFORMANCE ${results.status}`);if(results.status!=='PASS')process.exitCode=1;
}finally{await browser.close();}

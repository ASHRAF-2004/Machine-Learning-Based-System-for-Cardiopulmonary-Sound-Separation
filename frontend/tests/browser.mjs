import {chromium} from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..'),out=path.join(root,'evidence/winter-glass/integration');await fs.mkdir(out,{recursive:true});
const base=process.env.STETHOFUSE_TEST_URL||process.env.FRONTEND_URL||'http://127.0.0.1:4180';
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1});const page=await context.newPage();const errors=[],requests=[],responses=[],manifests=[],checks=[],routes=[],metrics={};
page.on('pageerror',e=>errors.push(e.message));
page.on('request',r=>requests.push(r.url()));
page.on('response',r=>{responses.push({url:r.url(),status:r.status()});if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);if(/\/assets\/owl\/[^/]+\/manifest\.json$/.test(new URL(r.url()).pathname))manifests.push(r);});
const check=(name,pass,detail)=>{checks.push({name,status:pass?'PASS':'FAIL',detail});console.log(`${pass?'PASS':'FAIL'} ${name}`);};
const wait=ms=>page.waitForTimeout(ms);
async function go(route){await page.goto(new URL(route,base).href);await page.locator('h1').first().waitFor({timeout:15000});await page.evaluate(()=>document.fonts.ready);await wait(180);}
async function persona(id){await page.evaluate(id=>sessionStorage.setItem('stethofuse-demo-persona',id),id);}
const owl=page.locator('.winter-hero .owl-art');
const owlState=()=>owl.evaluate(el=>({renderer:el.dataset.renderer,renderMode:el.dataset.renderMode,sourceViews:Number(el.dataset.sourceViews),yaw:Number(el.dataset.yaw),pitch:Number(el.dataset.pitch),targetYaw:Number(el.dataset.targetYaw),targetPitch:Number(el.dataset.targetPitch),drawCount:Number(el.dataset.drawCount),fallback:el.dataset.fallback||null,ready:el.querySelector('canvas')?.classList.contains('ready')||false}));
function posterState(el){const poster=el.querySelector('img'),canvas=el.querySelector('canvas');return {fallback:el.dataset.fallback||null,posterLoaded:!!poster&&poster.complete&&poster.naturalWidth>0,posterOpacity:poster?Number(getComputedStyle(poster).opacity):0,canvasReady:canvas?.classList.contains('ready')||false};}
async function visitRoutes(role,inventory){for(const [route,expectedHeading] of inventory){await go(route);const heading=await page.locator('h1').first().innerText(),actualPath=new URL(page.url()).pathname;routes.push({role,route,expectedHeading,heading,actualPath,url:page.url(),pass:actualPath===route&&heading===expectedHeading});}}
try {
 await go('/');
 await page.waitForFunction(()=>document.querySelector('.winter-hero .owl-art')?.dataset.renderer==='continuous-surface',null,{timeout:30000});
 const manifestResponse=manifests.at(-1);
 if(!manifestResponse)throw new Error('The continuous renderer did not request an owl manifest.');
 const manifest=await manifestResponse.json(),manifestUrl=manifestResponse.url(),info=await owl.evaluate(el=>el.owlInfo);
 const expected={fieldVersion:manifest.version,sourceViews:manifest.views.length,sourceTextureBytes:manifest.views.length*manifest.width*manifest.height*4,
  compressedBytes:manifest.views.reduce((s,v)=>s+v.bytes,0)+manifest.edges.reduce((s,e)=>s+e.bytes,0)+manifest.meshes.reduce((s,m)=>s+m.positions.bytes+m.indices.bytes,0),
  flowBufferBytes:manifest.edges.reduce((s,e)=>s+(e.decodedBytes||e.bytes),0),meshBufferBytes:manifest.meshes.reduce((s,m)=>s+m.positions.decodedBytes+m.indices.decodedBytes,0)};
 const requiredAssets=new Set([manifestUrl,...manifest.views.map(v=>new URL(v.texture,manifestUrl).href),...manifest.edges.map(e=>new URL(e.file,manifestUrl).href),...manifest.meshes.flatMap(m=>[m.positions.file,m.indices.file].map(file=>new URL(file,manifestUrl).href)),new URL(manifest.bodyTexture||'/assets/owl/body.webp',manifestUrl).href]);
 const initialAssets=requests.filter(url=>requiredAssets.has(url)),missingAssets=[...requiredAssets].filter(url=>!initialAssets.includes(url));
 metrics.owl={manifestUrl,revision:manifest.revision,width:manifest.width,height:manifest.height,info,expected,requiredAssetCount:requiredAssets.size};
 check('Continuous owl source count and decoded buffers match its loaded manifest',!!info&&Object.entries(expected).every(([key,value])=>info[key]===value)&&expected.sourceViews>2,{info,expected,note:'Source RGBA, flow and mesh buffers only; excludes body, canvas, GPU targets and other browser memory.'});
 check('Continuous owl loads each required source asset once',missingAssets.length===0&&initialAssets.length===requiredAssets.size,{expected:requiredAssets.size,requests:initialAssets.length,missingAssets});
 await page.screenshot({path:path.join(out,'welcome-1440.png'),fullPage:true});
 const hero=await page.locator('.winter-hero').boundingBox(),viewport=page.viewportSize();
 const visibleTop=Math.max(0,hero.y),visibleBottom=Math.min(viewport.height,hero.y+hero.height);
 const positions=[[.08,.18],[.5,.18],[.96,.18],[.08,.47],[.5,.47],[.96,.47],[.08,.77],[.5,.77],[.96,.77]];
 const states=[],assetsBeforeMotion=requests.filter(url=>requiredAssets.has(url)).length,drawBeforeMotion=(await owlState()).drawCount;
 for(const [index,[x,y]] of positions.entries()){
  await page.mouse.move(hero.x+hero.width*x,visibleTop+(visibleBottom-visibleTop)*y,{steps:12});
  await page.waitForFunction(()=>{const d=document.querySelector('.winter-hero .owl-art')?.dataset;return d&&Math.abs(Number(d.yaw)-Number(d.targetYaw))<.03&&Math.abs(Number(d.pitch)-Number(d.targetPitch))<.03;},null,{timeout:5000});
  states.push(await owlState());await page.locator('.winter-hero').screenshot({path:path.join(out,`owl-region-${index}.png`)});
 }
 const distinctPoses=new Set(states.map(s=>`${s.yaw.toFixed(2)},${s.pitch.toFixed(2)}`)).size;
 check('Continuous owl follows nine pointer regions within its nominal envelope',states.every(s=>s.renderer==='continuous-surface'&&s.ready&&!s.fallback&&Number.isFinite(s.yaw)&&Number.isFinite(s.pitch)&&Math.hypot(s.yaw/30,s.pitch/18)<=1.001)&&distinctPoses>4&&states.at(-1).drawCount>drawBeforeMotion,{distinctPoses,states});
 check('Pointer motion makes no additional source asset requests',requests.filter(url=>requiredAssets.has(url)).length===assetsBeforeMotion,{before:assetsBeforeMotion,after:requests.filter(url=>requiredAssets.has(url)).length});
 const art=await owl.boundingBox();await page.mouse.move(art.x+art.width*497.5/1163,art.y+art.height*260/1353,{steps:10});
 await page.waitForFunction(()=>{const d=document.querySelector('.winter-hero .owl-art')?.dataset;return d&&Math.abs(Number(d.yaw))<.03&&Math.abs(Number(d.pitch))<.03;},null,{timeout:5000});
 const neutral=await owlState();check('Pointer on the face returns to neutral',Math.abs(neutral.yaw)<.03&&Math.abs(neutral.pitch)<.03,neutral);
 await page.evaluate(()=>window.scrollTo(0,document.documentElement.scrollHeight));await wait(350);
 const offscreen=await owl.evaluate(el=>{const b=el.getBoundingClientRect();return b.bottom<=0||b.top>=innerHeight;}),before=(await owlState()).drawCount;
 await wait(350);const after=(await owlState()).drawCount;check('Offscreen owl stops drawing',offscreen&&before===after,{offscreen,before,after});
 await persona('USR-1001');
 await visitRoutes('staff',[
  ['/app/dashboard','A clear place to listen, Amina.'],['/app/recordings','My recordings'],['/app/recordings/new','A recording is the starting point.'],
  ['/app/recordings/new/upload','Bring your recording in.'],['/app/recordings/new/record','A quiet moment to record.'],['/app/recordings/REC-1042','Morning chest recording'],
  ['/app/processing','Ensemble processing'],['/app/processing/JOB-2100','Your demo outputs are ready.'],['/app/results','Results, with their context.'],
  ['/app/results/RES-3100','Morning chest recording'],['/app/history','Processing history'],['/app/shared','Shared & assigned'],
  ['/app/notifications','Notifications'],['/app/profile','Profile'],['/app/settings','Make room for your way of working.'],['/app/help','A little clarity, when you need it.'],
 ]);
 await go('/app/dashboard');await page.screenshot({path:path.join(out,'staff-dashboard-1440.png'),fullPage:true});
 await go('/app/results/RES-3100');await page.screenshot({path:path.join(out,'results-waveforms-1440.png'),fullPage:true});await page.getByRole('tab',{name:'Spectrograms',exact:true}).click();await wait(500);await page.screenshot({path:path.join(out,'results-spectrograms-1440.png'),fullPage:true});
 await page.getByRole('button',{name:'Play heart',exact:true}).click();await wait(350);check('Synthetic heart playback starts',await page.getByRole('button',{name:'Pause heart',exact:true}).isVisible());await page.getByRole('button',{name:'Pause heart',exact:true}).click();
 await persona('USR-2001');await visitRoutes('analyst',[
  ['/app/review-queue','Review queue'],['/app/assigned','Assigned to me'],['/app/reviews/ASN-401','Morning chest recording'],['/app/review-history','Review history'],
 ]);await go('/app/reviews/ASN-401');await page.screenshot({path:path.join(out,'analyst-review-1440.png'),fullPage:true});
 await persona('USR-3001');await visitRoutes('admin',[
  ['/app/admin','A clear view of the workspace.'],['/app/admin/users','People & permissions'],['/app/admin/users/USR-1001','Amina Rahman'],
  ['/app/admin/records','Recording operations'],['/app/admin/assignments','Assignments & access'],['/app/admin/ensemble','Ensemble configuration'],
  ['/app/admin/audit','Audit trail'],['/app/admin/settings','System preferences'],
 ]);
 await go('/app/admin');await page.screenshot({path:path.join(out,'admin-overview-1440.png'),fullPage:true});
 await go('/app/recordings/REC-1042');check('Admin role alone cannot access private recording',/restricted|access|permission|authorized|403/i.test(await page.locator('main').innerText())&&await page.locator('.audio-workbench').count()===0);
 await persona('USR-1002');await go('/app/recordings');check('Staff B cannot see Staff A recording title',!(await page.locator('main').innerText()).includes('Morning chest recording'));
 await go('/app/admin/users');check('Staff cannot enter administrator routes',page.url().endsWith('/403'));
 for(const width of [1920,768,390,360]){
  await page.setViewportSize({width,height:width>1000?1080:844});await go('/');await page.screenshot({path:path.join(out,`welcome-${width}.png`),fullPage:true});check(`Welcome no page overflow at ${width}`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await persona('USR-1001');await go('/app/dashboard');await page.screenshot({path:path.join(out,`dashboard-${width}.png`),fullPage:true});check(`Workspace no page overflow at ${width}`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  if(width<900){
   await page.getByRole('button',{name:'Open navigation',exact:true}).click();await page.waitForFunction(()=>Math.abs(document.querySelector('.sidebar').getBoundingClientRect().x)<.1);check(`Mobile drawer opens at ${width}`,await page.locator('.sidebar.open').count()===1);await page.screenshot({path:path.join(out,`navigation-${width}.png`)});
   // A full-screen backdrop's center sits behind the drawer on narrow phones.
   // Exercise the exposed backdrop with a real pointer click, never a force click.
   const backdrop=page.getByRole('button',{name:'Close navigation',exact:true}),bounds=await backdrop.boundingBox();
   await backdrop.click({position:{x:bounds.width-8,y:Math.min(100,bounds.height/2)}});
   await page.waitForFunction(()=>!document.querySelector('.sidebar').classList.contains('open'));
   check(`Mobile drawer closes from the exposed backdrop at ${width}`,await page.locator('.sidebar.open').count()===0);
  }
 }
 await page.setViewportSize({width:1440,height:900});await persona('USR-1001');await go('/app/settings');await page.keyboard.press('Tab');check('Keyboard focus reaches interactive element',await page.evaluate(()=>['A','BUTTON','INPUT','SELECT'].includes(document.activeElement.tagName)));
 const reduced=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'}),rp=await reduced.newPage(),rr=[];
 rp.on('request',r=>rr.push(r.url()));rp.on('pageerror',e=>errors.push(`Reduced motion: ${e.message}`));
 await rp.goto(base);await rp.locator('h1').first().waitFor();await rp.mouse.move(1400,300);await rp.waitForTimeout(600);
 const reducedState=await rp.locator('.winter-hero .owl-art').evaluate(posterState),fieldRequests=rr.filter(url=>new URL(url).pathname.startsWith('/assets/owl/'));
 check('Reduced motion keeps the poster without fetching continuous-surface assets',fieldRequests.length===0&&reducedState.posterLoaded&&reducedState.posterOpacity>.95&&!reducedState.canvasReady,{state:reducedState,fieldRequests});
 await rp.screenshot({path:path.join(out,'reduced-motion.png')});await reduced.close();
 const fallback=await browser.newContext({viewport:{width:1440,height:900}}),fp=await fallback.newPage();let blockedManifests=0;
 fp.on('pageerror',e=>errors.push(`Missing manifest: ${e.message}`));
 await fp.route(manifestUrl,route=>{blockedManifests++;return route.fulfill({status:404,contentType:'text/plain',body:'Intentional current-manifest fallback test'});});
 await fp.goto(base);await fp.locator('h1').first().waitFor();
 await fp.waitForFunction(()=>document.querySelector('.winter-hero .owl-art')?.dataset.fallback==='surface-unavailable',null,{timeout:15000});
 const fallbackState=await fp.locator('.winter-hero .owl-art').evaluate(posterState);
 check('Missing current manifest retains the loaded static poster',blockedManifests===1&&fallbackState.fallback==='surface-unavailable'&&fallbackState.posterLoaded&&fallbackState.posterOpacity>.95&&!fallbackState.canvasReady,{manifestUrl,blockedManifests,state:fallbackState});
 await fp.screenshot({path:path.join(out,'missing-manifest-fallback.png')});await fallback.close();
 check('All 28 required app routes retain their expected path and screen heading',routes.length===28&&routes.every(r=>r.pass),{count:routes.length,mismatches:routes.filter(r=>!r.pass)});
 check('No unexpected browser errors or missing resources',errors.length===0,errors);
}catch(error){checks.push({name:'Browser test execution',status:'FAIL',detail:error.stack});console.error(error);}
finally{await fs.writeFile(path.join(out,'results.json'),JSON.stringify({testedAt:new Date().toISOString(),browser:await browser.version(),base,scope:'Development demonstration: current continuous-surface smoke checks, expected route screens, role boundaries and responsive layout. Viewport emulation, not physical devices or comprehensive owl motion/performance certification.',routes,metrics,checks,errors,responses},null,2));await browser.close();}
if(checks.some(c=>c.status==='FAIL'))process.exitCode=1;

import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {access,mkdir,readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';

const root=path.resolve(import.meta.dirname,'..');
const output=path.resolve(root,process.env.EVIDENCE_ROOT||'evidence/public-reference/final','motion');
const base=process.env.FRONTEND_URL||'http://127.0.0.1:4180';
try{await access(output);throw new Error(`Refusing to overwrite existing evidence: ${output}`);}catch(error){if(error.code!=='ENOENT')throw error;}
await mkdir(output,{recursive:true});
const checks=[],errors=[],metrics={};
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
async function check(name,action){try{const detail=await action();checks.push({name,status:'PASS',detail});console.log(`PASS ${name}`);}catch(error){checks.push({name,status:'FAIL',error:error.stack});console.error(`FAIL ${name}: ${error.message}`);process.exitCode=1;}}
async function openPage(options={}){
 const context=await browser.newContext({viewport:{width:1536,height:1024},deviceScaleFactor:1,...options});
 const page=await context.newPage(),requests=[];
 page.on('request',request=>requests.push({url:request.url(),method:request.method()}));
 page.on('pageerror',error=>errors.push(error.message));
 page.on('response',response=>{if(response.status()>=400)errors.push(`${response.status()} ${response.url()}`);});
 await page.goto(base,{waitUntil:'domcontentloaded'});await page.locator('h1').first().waitFor();await page.evaluate(()=>document.fonts.ready);
 return{context,page,requests};
}
const state=page=>page.locator('.winter-hero .owl-art').evaluate(element=>({
 renderer:element.dataset.renderer||null,renderMode:element.dataset.renderMode||null,sourceViews:Number(element.dataset.sourceViews||0),
 yaw:Number(element.dataset.yaw||0),pitch:Number(element.dataset.pitch||0),targetYaw:Number(element.dataset.targetYaw||0),targetPitch:Number(element.dataset.targetPitch||0),drawCount:Number(element.dataset.drawCount||0),
 fallback:element.dataset.fallback||null,ready:element.querySelector('canvas')?.classList.contains('ready')||false,
 posterLoaded:!!element.querySelector('img')?.naturalWidth,posterOpacity:Number(getComputedStyle(element.querySelector('img')).opacity),
}));
try{
 await check('Protected controller, adapter, brand and identity hashes match their checkpoints',async()=>{
  const checkpoint=JSON.parse(await readFile(path.join(root,'evidence/public-reference/checkpoint/metrics.json'),'utf8'));
  const identities=JSON.parse(await readFile(path.join(root,'evidence/assets/optimization.json'),'utf8')).identity_assets;
  const staticAssets=JSON.parse(await readFile(path.join(root,'evidence/owl-diagonal-repair/source-verification.json'),'utf8')).protected;
  const rows=['src/components/Owl.tsx','src/components/owlCanvasSurface.ts','src/data/adapters.ts','src/brand.ts'].map(file=>({file:path.join(root,file),expected:checkpoint.sourceHashes[file],baseline:'public-reference/checkpoint/metrics.json'}));
  rows.push(...identities.map(row=>({file:row.source,expected:row.sha256,baseline:'assets/optimization.json'})));
  rows.push({file:path.join(root,'public/assets/logo.svg'),expected:identities.find(row=>row.source.endsWith('StethoFuse_owl_logo.svg')).sha256,baseline:'assets/optimization.json'});
  rows.push(...staticAssets.map(row=>({file:row.path,expected:row.expected,baseline:'owl-diagonal-repair/source-verification.json'})));
  for(const row of rows){row.actual=createHash('sha256').update(await readFile(row.file)).digest('hex');row.matches=row.actual===row.expected;}
  metrics.protectedFiles=rows;assert(rows.every(row=>row.matches));return{checked:rows.length,mismatches:rows.filter(row=>!row.matches)};
 });
 await check('Normal home loads the approved connected-neck continuous owl',async()=>{
  const {context,page,requests}=await openPage();
  try{
   await page.waitForFunction(()=>document.querySelector('.winter-hero .owl-art')?.dataset.renderer==='continuous-surface',null,{timeout:30000});
   const manifest=JSON.parse(await readFile(path.join(root,'public/assets/owl/neck-candidate/manifest.json'),'utf8'));
   const initial=await state(page);assert(initial.ready);assert.equal(initial.fallback,null);assert.equal(initial.sourceViews,manifest.views.length);
   assert(requests.some(request=>new URL(request.url).pathname==='/assets/owl/neck-candidate/manifest.json'));
   metrics.desktop={initial,info:await page.locator('.owl-art').evaluate(element=>element.owlInfo)};
   await page.screenshot({path:path.join(output,'desktop-ready-1536.png')});
   const hero=await page.locator('.winter-hero').boundingBox(),art=await page.locator('.winter-hero .owl-art').boundingBox();
   const top=Math.max(0,hero.y),bottom=Math.min(1024,hero.y+hero.height);
   const face={x:art.x+art.width*497.5/1163,y:art.y+art.height*260/1353};
   const radiusX=Math.min(240,face.x-hero.x-20,hero.x+hero.width-face.x-20),radiusY=Math.min(125,face.y-top-20,bottom-face.y-20);
   assert(radiusX>35&&radiusY>35,'Owl face needs enough visible hero space for a real pointer circle.');
   const assetsBefore=requests.filter(request=>new URL(request.url).pathname.startsWith('/assets/owl/')).length;
   const samples=[];
   for(let index=0;index<=16;index++){
    const angle=index/16*Math.PI*2,x=face.x+radiusX*Math.cos(angle),y=face.y+radiusY*Math.sin(angle);
    await page.mouse.move(x,y,{steps:3});await page.waitForTimeout(90);
    samples.push({pointer:{x,y},...await state(page)});
   }
   await page.waitForFunction(()=>{const d=document.querySelector('.winter-hero .owl-art')?.dataset;return d&&Math.abs(Number(d.yaw)-Number(d.targetYaw))<.03&&Math.abs(Number(d.pitch)-Number(d.targetPitch))<.03;},null,{timeout:5000});
   const hold=await state(page),yawRange=Math.max(...samples.map(s=>s.yaw))-Math.min(...samples.map(s=>s.yaw)),pitchRange=Math.max(...samples.map(s=>s.pitch))-Math.min(...samples.map(s=>s.pitch));
   metrics.desktop={...metrics.desktop,hero,art,face,radiusX,radiusY,samples,hold,yawRange,pitchRange};
   assert(yawRange>8,`Insufficient actual yaw response: ${yawRange}`);assert(pitchRange>8,`Insufficient actual pitch response: ${pitchRange}`);
   assert(samples.some(sample=>sample.yaw>2)&&samples.some(sample=>sample.yaw< -2));assert(samples.some(sample=>sample.pitch>2)&&samples.some(sample=>sample.pitch< -2));
   assert(hold.drawCount>initial.drawCount+10);assert(samples.every(sample=>sample.ready&&!sample.fallback&&Math.hypot(sample.yaw/30,sample.pitch/18)<=1.001));
   assert.equal(requests.filter(request=>new URL(request.url).pathname.startsWith('/assets/owl/')).length,assetsBefore);
   await page.screenshot({path:path.join(output,'desktop-after-circle-hold.png')});
   return{sourceViews:initial.sourceViews,renderMode:initial.renderMode,yawRange,pitchRange,draws:hold.drawCount-initial.drawCount,realPointerSamples:samples.length,noAdditionalAssetRequests:true};
  }finally{await context.close();}
 });
 for(const variant of [{name:'reduced-motion',options:{reducedMotion:'reduce'}},{name:'mobile-touch',options:{viewport:{width:390,height:844},isMobile:true,hasTouch:true,reducedMotion:'no-preference'}}])await check(`${variant.name} keeps the approved static poster without surface downloads`,async()=>{
  const {context,page,requests}=await openPage(variant.options);
  try{
   await page.locator('.winter-hero .owl-art img').evaluate(image=>image.decode());
   if(variant.name==='mobile-touch'){
    const art=await page.locator('.winter-hero .owl-art').boundingBox();
    await page.touchscreen.tap(Math.min(380,art.x+art.width/2),Math.min(834,art.y+art.height/3));
   }else await page.mouse.move(1300,300,{steps:8});
   await page.waitForTimeout(650);
   const actual=await state(page),fieldRequests=requests.filter(request=>new URL(request.url).pathname.startsWith('/assets/owl/'));
   const media=await page.evaluate(()=>({fine:matchMedia('(pointer: fine)').matches,coarse:matchMedia('(pointer: coarse)').matches,reduced:matchMedia('(prefers-reduced-motion: reduce)').matches}));
   assert(actual.posterLoaded);assert(actual.posterOpacity>.95);assert.equal(actual.ready,false);assert.equal(actual.drawCount,0);assert.equal(fieldRequests.length,0);
   if(variant.name==='mobile-touch')assert.equal(media.fine,false);else assert.equal(media.reduced,true);
   metrics[variant.name]={actual,media,fieldRequests};await page.screenshot({path:path.join(output,`${variant.name}.png`),fullPage:variant.name==='mobile-touch'});
   return{...actual,media,fieldRequests:fieldRequests.length};
  }finally{await context.close();}
 });
 await check('Checked remember option discloses unavailable persistence and never stores credentials or a session',async()=>{
  const {context,page,requests}=await openPage({reducedMotion:'reduce'});
  try{
   await page.goto(base+'/login');await page.locator('h1').waitFor();
   const checkbox=page.getByRole('checkbox',{name:'Keep me signed in',exact:true});await checkbox.check();
   const note=page.locator('#persistence-unavailable');await note.waitFor();
   assert.match(await note.innerText(),/requires connected authentication/);assert.match(await note.innerText(),/does not save credentials or create a session/);
   assert.equal(await checkbox.getAttribute('aria-describedby'),'persistence-unavailable');
   const email='fictional-remember-check@example.test',password='DEMO-remember-secret-8294';
   await page.locator('input[name="email"]').fill(email);await page.getByLabel('Password',{exact:true}).fill(password);
   await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.getByText(/Live sign-in is not connected/).waitFor();
   assert.equal(await page.getByLabel('Password',{exact:true}).inputValue(),'');
   const storage=await page.evaluate(()=>({values:JSON.stringify({...localStorage,...sessionStorage}),persona:sessionStorage.getItem('stethofuse-demo-persona')}));
   assert(!storage.values.includes(email));assert(!storage.values.includes(password));assert.equal(storage.persona,null);
   assert(requests.every(request=>request.method==='GET'));assert(requests.every(request=>request.url.startsWith(base)||request.url.startsWith('data:')||request.url.startsWith('blob:')));
   await page.screenshot({path:path.join(output,'remember-disconnected.png')});
   await page.reload();await page.locator('h1').waitFor();assert.equal(await page.getByRole('checkbox',{name:'Keep me signed in',exact:true}).isChecked(),false);
   return{disclosure:'visible and associated with checkbox',passwordCleared:true,credentialPersistence:false,sessionCreated:false,rememberPersistsAfterReload:false,externalRequests:0,nonGetRequests:0};
  }finally{await context.close();}
 });
 await check('No browser runtime errors or failed resources',async()=>{assert.deepEqual(errors,[]);return errors;});
}finally{
 await writeFile(path.join(output,'results.json'),JSON.stringify({testedAt:new Date().toISOString(),browser:await browser.version(),base,scope:'Focused real-pointer circle/hold, reduced-motion and mobile-touch static behavior, protected hashes and disconnected remember option. Headless viewport/touch emulation, not physical-device or comprehensive motion certification.',checks,metrics,errors},null,2));
 await browser.close();
}

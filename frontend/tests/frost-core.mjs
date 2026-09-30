// LOCAL acceptance: real API/proxy/SQLite/private WAVs/frozen CPU worker.
// ONLY identity is substituted by the existing test SDK/verifier. No runtime bypass.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {access,mkdir,readFile,writeFile,stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';

const root=path.resolve('..'),python=path.join(root,'.local/ml-integration/venv/bin/python');
const output=path.resolve(process.env.EVIDENCE_ROOT||'output/playwright/frost-core/integration-v1');
const runtime=path.join(root,'.local/frost-core-runtime');
const checkpoint=path.resolve(root,'.local/training/stethofuse-tcn-v1/pre-t9-family-refit-v1/refit-all-nontest-seed20260928/checkpoints/endpoint.pt');
const spec=path.join(root,'research/configs/final_separator_v2.json');
const expectedCheckpoint='1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658';
const expectedSpec='2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
function wavChunk(bytes,name){
  for(let at=12;at+8<=bytes.length;){const size=bytes.readUInt32LE(at+4);assert(at+8+size<=bytes.length);if(bytes.toString('ascii',at,at+4)===name)return bytes.subarray(at+8,at+8+size);at+=8+size+(size%2);}
  throw new Error(`WAV ${name} chunk missing`);
}
assert.equal(hash(await readFile(checkpoint)),expectedCheckpoint);
assert.equal(hash(await readFile(spec)),expectedSpec);
try{await access(output);throw new Error('Evidence exists; choose a new versioned directory.');}catch(e){if(e.code!=='ENOENT')throw e;}
await mkdir(output,{recursive:true});await mkdir(runtime,{recursive:true,mode:0o700});
assert.equal((await stat(runtime)).mode&0o077,0);
const base='http://127.0.0.1:4194';
try{await fetch(base,{signal:AbortSignal.timeout(1000)});throw new Error('Acceptance port already in use; do not disturb it.');}catch(e){if(!['TypeError','TimeoutError'].includes(e.name))throw e;}

const n=60000,wav=Buffer.alloc(44+2*n);
wav.write('RIFF');wav.writeUInt32LE(36+2*n,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);
wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(4000,24);wav.writeUInt32LE(8000,28);
wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(2*n,40);
for(let i=0;i<n;i++){
  const pulse=Math.exp(-(((i%3200)-480)**2)/18000)*Math.sin(2*Math.PI*75*i/4000);
  const breath=(0.35+0.3*Math.sin(2*Math.PI*0.25*i/4000))*Math.sin(2*Math.PI*430*i/4000);
  wav.writeInt16LE(Math.round(7500*pulse+2400*breath),44+2*i);
}
await writeFile(path.join(output,'M0001.wav'),wav);
const fixture=new URL('./m1/ml_fixture.py',import.meta.url).pathname;
const checks=[],errors=[],screenshots=[],traffic=[];
const layoutOnly=process.argv.includes('--layout-only');
let apiServer,vite,worker,browser,info,result,record,job,workerReceipt;
let serverLog='',workerLog='',frontendLog='';
const startedAt=new Date().toISOString();
async function check(name,fn){
  if(layoutOnly&&!name.startsWith('REAL API empty Overview')&&!name.startsWith('REAL integrated owl'))return;
  try{await fn();checks.push({name,status:'PASS'});console.log('PASS',name);}
  catch(error){checks.push({name,status:'FAIL',error:error.message});throw error;}
}
async function waitHealth(url,child){
  for(let i=0;i<100;i++){
    if(child.exitCode!==null)throw new Error('Local process exited before health check.');
    try{if((await fetch(url)).ok)return;}catch{}
    await new Promise(resolve=>setTimeout(resolve,100));
  }
  throw new Error('Local health timeout.');
}
const exit=child=>new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',code=>code===0?resolve():reject(new Error(`Local process exit ${code}`)));});
async function stop(child){if(!child||child.exitCode!==null||child.signalCode!==null)return;child.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{child.kill('SIGKILL');resolve();},5000);child.once('exit',()=>{clearTimeout(timer);resolve();});});}
try{
  apiServer=spawn(python,[fixture],{cwd:root,env:{...process.env,TMPDIR:runtime},stdio:['ignore','pipe','pipe']});
  apiServer.stderr.on('data',d=>serverLog+=d);
  info=await new Promise((resolve,reject)=>{
    let text='';apiServer.stdout.on('data',d=>{text+=d;if(text.includes('\n'))resolve(JSON.parse(text.split('\n')[0]));});
    apiServer.once('exit',code=>reject(new Error(`API fixture exit ${code}`)));
    setTimeout(()=>reject(new Error('API fixture startup timeout')),15000).unref();
  });
  const api=`http://127.0.0.1:${info.port}`,headers=uid=>({Authorization:`Bearer M1-MOCK:${uid}`});
  assert.equal(info.host,'127.0.0.1');
  for(const value of [info.database,info.privateStorage,info.workerLock])assert(value.startsWith(runtime+'/stethofuse-ml-browser-'));
  console.log('ISOLATED',JSON.stringify(info));
  await waitHealth(api+'/health',apiServer);
  vite=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','4194','--strictPort'],{env:{...process.env,STETHOFUSE_API_PROXY:api},stdio:['ignore','pipe','pipe']});
  vite.stdout.on('data',d=>frontendLog+=d);vite.stderr.on('data',d=>frontendLog+=d);
  await waitHealth(base,vite);
  // Ordinary browser launch. No disabled sandbox/security flags or production profile.
  browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',`--use-file-for-fake-audio-capture=${path.join(output,'M0001.wav')}`]});
  async function context(){
    const c=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce',acceptDownloads:true,permissions:['microphone']});
    await c.route('**/node_modules/.vite/deps/firebase_app.js*',r=>r.fulfill({contentType:'application/javascript',path:new URL('./m1/mock-firebase-app.mjs',import.meta.url).pathname}));
    await c.route('**/node_modules/.vite/deps/firebase_auth.js*',r=>r.fulfill({contentType:'application/javascript',path:new URL('./m1/mock-firebase-auth.mjs',import.meta.url).pathname}));
    await c.route('**/src/config/runtime.ts*',r=>r.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
    // API requests are NOT intercepted: real Vite loopback proxy -> real local API.
    await c.route(url=>['http:','https:'].includes(url.protocol)&&url.origin!==base,r=>{errors.push('Unexpected external request blocked');return r.abort();});
    c.on('page',p=>{p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{const url=new URL(r.url());if(url.pathname.startsWith('/api/'))traffic.push({path:url.pathname,method:r.request().method(),status:r.status()});});});
    await c.addInitScript(()=>{
      window.__frostUrls={created:0,revoked:0};
      const create=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL);
      URL.createObjectURL=blob=>{window.__frostUrls.created++;return create(blob);};
      URL.revokeObjectURL=url=>{window.__frostUrls.revoked++;return revoke(url);};
    });
    return c;
  }
  async function signIn(page,uid){
    await page.goto(base+'/login');await page.getByRole('textbox',{name:'Email address',exact:true}).fill(uid+'@example.invalid');
    await page.getByLabel('Password',{exact:true}).fill('Fictional-local-only');
    await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.locator('[data-live-workspace=true]').waitFor();
  }
  const owner=await context(),page=await owner.newPage();
  async function shot(name,page,fullPage=false){
    await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(output,name),fullPage});
    screenshots.push({name,viewport:page.viewportSize(),sha256:hash(await readFile(path.join(output,name)))});
  }
  async function readyPlayers(page,count=3){await page.waitForFunction(n=>document.querySelectorAll('.sf-player[data-media-state="ready"]').length===n,count);}
  async function grant(permission,resource_id){
    const response=await fetch(api+`/api/recordings/${record.id}/grants`,{method:'POST',headers:{...headers('alice'),'Content-Type':'application/json'},body:JSON.stringify({recipient_id:info.analystId,permission,resource_id})});
    assert.equal(response.status,201);return response.json();
  }

  await check('REAL API empty Overview, authenticated logo and no preview identities/banners',async()=>{
    await signIn(page,'alice');await page.getByRole('heading',{name:'Your next recording starts here'}).waitFor();
    assert.equal(await page.getByText('Local design preview',{exact:true}).count(),0);
    assert.equal(await page.getByText('@silverdragonfly',{exact:true}).count(),0);
    await shot('00-overview-empty-desktop.png',page);
    await page.getByRole('link',{name:'StethoFuse Overview',exact:true}).click();await page.waitForURL('**/app/overview');
  });
  await check('REAL upload/review M0001.wav -> persisted Library identity',async()=>{
    await page.goto(base+'/app/recordings/new/upload');
    await page.locator('input[type=file]').setInputFiles({name:'M0001.wav',mimeType:'audio/wav',buffer:wav});
    await page.getByLabel('Recording title',{exact:true}).fill('Synthetic morning study — quiet room reference');
    await readyPlayers(page,1);await shot('03-upload-review-desktop.png',page);
    await page.getByRole('button',{name:'Upload recording',exact:true}).click();
    await page.getByRole('heading',{name:'Synthetic morning study — quiet room reference',exact:true}).waitFor();
    record=(await(await fetch(api+'/api/recordings',{headers:headers('alice')})).json()).items[0];
    assert.equal(record.original_filename,'M0001.wav');await readyPlayers(page,1);
    await page.goto(base+'/app/library');await page.getByText(record.title,{exact:true}).waitFor();
    await shot('02-library-recorded-desktop.png',page);
  });
  await check('REAL quick separation request -> durable queued state, repeated request reuses job',async()=>{
    await page.goto(base+`/app/recordings/${record.id}`);await readyPlayers(page,1);
    const began=performance.now();await page.getByRole('button',{name:'Separate',exact:true}).click();
    await page.getByRole('heading',{name:'Waiting to separate',exact:true}).waitFor();
    job=(await(await fetch(api+'/api/jobs',{headers:headers('alice')})).json()).items[0];
    assert.equal(job.status,'queued');job.requestObservationSeconds=(performance.now()-began)/1000;
    const repeated=await(await fetch(api+`/api/recordings/${record.id}/jobs`,{method:'POST',headers:{...headers('alice'),'Content-Type':'application/json'},body:'{}'})).json();
    assert.equal(repeated.id,job.id);await shot('04-queued-desktop.png',page);
  });
  await check('REAL unchanged frozen worker -> processing -> succeeded, no synthetic UI progress',async()=>{
    const workerEnv={...process.env,STETHOFUSE_M1_DATABASE:info.database,STETHOFUSE_M1_PRIVATE_STORAGE:info.privateStorage,STETHOFUSE_SEPARATION_ENABLED:'1',STETHOFUSE_MODEL_CHECKPOINT:checkpoint};
    worker=spawn(python,[fixture,'--worker'],{cwd:root,env:workerEnv,stdio:['pipe','pipe','pipe']});
    const finished=exit(worker);worker.stderr.on('data',d=>workerLog+=d);
    await new Promise((resolve,reject)=>{let text='';worker.stdout.on('data',d=>{text+=d;workerLog+=d;if(text.includes('READY_FOR_INFERENCE'))resolve();});worker.once('exit',code=>reject(new Error(`Worker exited early ${code}`)));setTimeout(()=>reject(new Error('Worker startup timeout')),20000).unref();});
    await page.getByRole('heading',{name:'Separation in progress',exact:true}).waitFor();
    await shot('05-processing-desktop.png',page);
    // Existing test-only observation barrier; no model/preprocessing/inference change.
    worker.stdin.end('continue\n');await finished;worker=null;
    await page.locator('.sf-detail-meta .sf-status--ready').waitFor();await readyPlayers(page);
    result=(await(await fetch(api+'/api/results',{headers:headers('alice')})).json()).items[0];
    assert.equal(result.provenance.output_samples,60000);assert.equal(result.provenance.checkpoint_sha256,expectedCheckpoint);assert.equal(result.provenance.separator_spec_sha256,expectedSpec);
    workerReceipt=result.provenance;await shot('06-ready-detail-frost-desktop.png',page);await shot('06b-ready-detail-frost-full.png',page,true);
  });
  await check('REAL auto media, unboosted analysis source switching, seek and 100/150/200% gain',async()=>{
    assert.equal(await page.getByRole('button',{name:'Load authorized file'}).count(),0);
    const originalRms=await page.locator('.sf-metric').filter({hasText:'RMS level'}).innerText();
    await page.getByRole('group',{name:'Analysis source',exact:true}).getByRole('button',{name:'Heart',exact:true}).click();
    const heartRms=await page.locator('.sf-metric').filter({hasText:'RMS level'}).innerText();assert.notEqual(originalRms,heartRms);
    const seek=page.getByRole('slider',{name:'Seek Heart',exact:true});await seek.focus();await seek.press('ArrowRight');assert(Number(await seek.inputValue())>0);
    const volume=page.getByRole('slider',{name:'Heart playback volume',exact:true});
    await volume.focus();await volume.press('Home');for(let i=0;i<20;i++)await volume.press('ArrowRight');assert.equal(await volume.inputValue(),'100');
    for(let i=0;i<10;i++)await volume.press('ArrowRight');assert.equal(await volume.inputValue(),'150');assert.equal(await volume.getAttribute('aria-valuetext'),'150 percent, boost enabled');
    await shot('07-ready-detail-boost150-desktop.png',page);await volume.press('End');assert.equal(await volume.inputValue(),'200');
    assert.equal(await page.locator('.sf-metric').filter({hasText:'RMS level'}).innerText(),heartRms);
    await page.getByRole('button',{name:'Play Heart',exact:true}).click();await page.getByRole('button',{name:'Pause Heart',exact:true}).waitFor();
    await page.getByRole('button',{name:'Play Lung',exact:true}).click();await page.getByRole('button',{name:'Pause Lung',exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Pause Heart',exact:true}).count(),0);
    await page.getByRole('button',{name:'Pause Lung',exact:true}).click();
  });
  await check('REAL downloaded output unchanged; float WAV samples finite, stored rate/length exact',async()=>{
    const heart=result.resources.find(r=>r.kind==='heart_audio');
    const bytes=Buffer.from(await(await fetch(api+heart.url,{headers:headers('alice')})).arrayBuffer());
    const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('link',{name:'Download Heart',exact:true}).click()]);
    assert.equal(hash(await readFile(await download.path())),hash(bytes));
    const original=Buffer.from(await(await fetch(api+`/api/media/${record.original_resource_id}`,{headers:headers('alice')})).arrayBuffer());assert.equal(hash(original),hash(wav));
    for(const resource of result.resources){
      const b=Buffer.from(await(await fetch(api+resource.url,{headers:headers('alice')})).arrayBuffer());
      const format=wavChunk(b,'fmt '),samples=wavChunk(b,'data');
      assert.equal(format.readUInt32LE(4),4000);assert.equal(format.readUInt16LE(2),1);assert.equal(samples.length/4,60000);
      for(let at=0;at<samples.length;at+=4)assert(Number.isFinite(samples.readFloatLE(at)));
    }
  });
  await check('REAL refresh/new authenticated session restores persisted state, legacy links preserve identities',async()=>{
    await page.reload();await readyPlayers(page);assert.equal(await page.getByRole('slider',{name:'Heart playback volume'}).inputValue(),'200');
    await page.goto(base+`/app/processing/${job.id}`);await page.waitForURL(`**/app/recordings/${record.id}`);await readyPlayers(page);
    await page.goto(base+`/app/results/${result.id}`);await readyPlayers(page,2);assert.equal(await page.getByRole('button',{name:'Play Original',exact:true}).count(),0);
    await page.goto(base+'/app/results');await page.waitForURL('**/app/library?filter=ready');await page.getByText(record.title,{exact:true}).waitFor();
    const fresh=await context(),p=await fresh.newPage();await signIn(p,'alice');await p.goto(base+`/app/recordings/${record.id}`);await readyPlayers(p);await fresh.close();
  });
  await check('REAL Overview/Library data, working search/filter/sort/pages, long title and missing display name',async()=>{
    for(let i=0;i<7;i++){
      const form=new FormData();form.set('file',new Blob([wav],{type:'audio/wav'}),'M0001.wav');form.set('title',i===0?'Synthetic reference — a deliberately long recording title that remains readable on laptop, tablet and mobile without a fabricated public identity':'Synthetic reference '+(i+1));
      assert.equal((await fetch(api+'/api/recordings',{method:'POST',headers:headers('alice'),body:form})).status,201);
    }
    await page.goto(base+'/app/library');await page.getByRole('button',{name:'Next page',exact:true}).waitFor();await page.getByRole('button',{name:'Next page',exact:true}).click();assert.match(await page.locator('.sf-library-footer').innerText(),/7–8 of 8/);
    await page.getByRole('searchbox').fill('morning study');await page.waitForFunction(()=>document.querySelectorAll('.sf-recordings li').length===1);assert.equal(await page.locator('.sf-recordings li').count(),1);
    await page.getByRole('button',{name:'Clear search',exact:true}).click();await page.getByRole('button',{name:/^Ready/}).click();await page.waitForFunction(()=>document.querySelectorAll('.sf-recordings li').length===1);assert.equal(await page.locator('.sf-recordings li').count(),1);
    await page.getByRole('button',{name:/^All/}).click();await page.waitForFunction(()=>document.querySelectorAll('.sf-recordings li').length===6);
    await page.getByRole('combobox',{name:'Sort recordings',exact:true}).selectOption('oldest');
    await page.waitForURL('**/app/library?**sort=oldest');assert.equal(await page.getByRole('combobox',{name:'Sort recordings',exact:true}).inputValue(),'oldest');assert.equal(await page.locator('.sf-recordings li').count(),6);
    await shot('02-library-light-desktop.png',page);
    await page.goto(base+'/app/overview');await page.locator('.sf-recordings li').first().waitFor();await shot('01-overview-light-desktop.png',page);
  });
  await check('REAL integrated owl: approved renderer, page-wide pointer tracking and unchanged perched assets',async()=>{
    await page.emulateMedia({reducedMotion:'no-preference'});await page.reload();
    await page.locator('.sf-owl.is-ready').waitFor();
    await page.mouse.move(15,850);await page.waitForFunction(()=>Number(document.querySelector('.sf-owl').dataset.targetYaw)<-1);
    const left=await page.locator('.sf-owl').getAttribute('data-target-yaw');
    await page.mouse.move(1420,500);await page.waitForFunction(left=>document.querySelector('.sf-owl').dataset.targetYaw!==left,left);
    assert.equal(await page.locator('.sf-owl').getAttribute('data-renderer'),'approved-connected-neck');
    await page.emulateMedia({reducedMotion:'reduce'});await page.reload();
    assert.equal(await page.locator('.sf-owl.is-ready').count(),0);
    for(const width of [1440,390]){
      await page.setViewportSize({width,height:width===390?844:900});
      assert.equal(await page.locator('.sf-botanical-perch').evaluate(e=>e.getBoundingClientRect().width),width===390?158:266);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      await shot(width===390?'18-overview-contact-mobile.png':'17-overview-contact-desktop.png',page);
      const bounds=await page.locator('.sf-greeting-art').boundingBox();
      const name=width===390?'owl-mobile-closeup.png':'owl-desktop-closeup.png';
      await page.screenshot({path:path.join(output,name),clip:{x:bounds.x-20,y:bounds.y,width:bounds.width+20,height:bounds.height+30}});
      screenshots.push({name,viewport:page.viewportSize(),sha256:hash(await readFile(path.join(output,name)))});
    }
    await page.setViewportSize({width:1440,height:900});
  });
  await check('REAL integrated Frost/Midnight/mobile/tablet, keyboard focus, reduced motion and no overflow',async()=>{
    await page.goto(base+`/app/recordings/${record.id}`);await readyPlayers(page);
    await page.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await shot('08-ready-detail-midnight-desktop.png',page);
    await page.getByRole('button',{name:'Switch to Frost theme',exact:true}).click();
    for(const width of [900,390]){
      await page.setViewportSize({width,height:width===390?844:1000});await readyPlayers(page);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      await shot(width===390?'09-ready-detail-mobile.png':'10-ready-detail-tablet.png',page,true);
    }
    const sources=page.getByRole('group',{name:'Audio source',exact:true});await sources.getByRole('button',{name:'Heart',exact:true}).click();
    const slider=page.getByRole('slider',{name:'Heart playback volume'});await slider.focus();await slider.press('ArrowRight');assert.equal(await slider.evaluate(e=>getComputedStyle(e).outlineStyle),'solid');await slider.press('Home');for(let i=0;i<30;i++)await slider.press('ArrowRight');assert.equal(await slider.inputValue(),'150');
    await shot('11-ready-detail-mobile-boost150.png',page,true);
    await page.goto(base+'/app/overview');await page.locator('.sf-recordings li').first().waitFor();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await shot('12-overview-mobile.png',page,true);
    assert.equal(await page.locator('.sf-owl.is-ready').count(),0); // Reduced motion keeps approved poster.
    await page.setViewportSize({width:1440,height:900});
  });
  await check('REAL anonymous/unrelated/exact Heart access, result metadata separately authorized',async()=>{
    const heart=result.resources.find(r=>r.kind==='heart_audio'),lung=result.resources.find(r=>r.kind==='lung_audio');
    assert.equal((await fetch(api+heart.url)).status,401);assert.equal((await fetch(api+heart.url,{headers:headers('bob')})).status,403);
    assert.equal((await fetch(api+heart.url,{headers:headers('analyst')})).status,403);
    const exact=await grant('read',heart.id);
    const analyst=await context(),p=await analyst.newPage();await signIn(p,'analyst');await p.goto(base+`/app/recordings/${record.id}`);await readyPlayers(p,1);
    assert.equal(await p.getByRole('button',{name:'Play Lung',exact:true}).count(),0);assert.equal(await p.getByRole('group',{name:'Analysis source'}).getByRole('button',{name:'Lung'}).count(),0);
    assert.equal((await fetch(api+lung.url,{headers:headers('analyst')})).status,403);assert.equal((await fetch(api+`/api/media/${record.original_resource_id}`,{headers:headers('analyst')})).status,403);
    assert.equal((await fetch(api+`/api/results/${result.id}`,{headers:headers('analyst')})).status,403);await shot('13-exact-heart-access.png',p);
    await p.goto(base+`/app/audio/${heart.id}`);await readyPlayers(p,1);assert.equal(await p.getByRole('button',{name:'Play Heart',exact:true}).count(),1);assert.equal(await p.getByRole('button',{name:'Play Original',exact:true}).count(),0);
    const metadata=await grant('review',result.id);await p.goto(base+`/app/results/${result.id}`);await readyPlayers(p,1);assert.equal(await p.getByRole('button',{name:'Play Lung',exact:true}).count(),0);
    await p.goto(base+`/app/reviews/${metadata.id}`);await p.getByLabel('Non-diagnostic notes',{exact:true}).waitFor();await readyPlayers(p,1);
    await p.goto(base+`/app/recordings/${record.id}`);await readyPlayers(p,1);await p.getByRole('button',{name:'Play Heart',exact:true}).click();
    assert.equal((await fetch(api+`/api/grants/${exact.id}`,{method:'DELETE',headers:headers('alice')})).status,204);
    await p.getByRole('button',{name:'Refresh access',exact:true}).click();
    await p.getByText(/No audio is included in your current access|Measurements are unavailable/).first().waitFor();
    assert.equal(await p.getByRole('button',{name:'Pause Heart',exact:true}).count(),0);
    assert.equal(await p.locator('.sf-signal-chart').count(),0);
    assert.equal((await fetch(api+heart.url,{headers:headers('analyst')})).status,403);
    await p.goto(base+`/app/results/${result.id}`);await p.getByText('No audio is included in your current access.',{exact:false}).waitFor();
    await fetch(api+`/api/grants/${metadata.id}`,{method:'DELETE',headers:headers('alice')});await p.reload();await p.getByText('You do not have permission for this action or resource.',{exact:true}).waitFor();
    await analyst.close();
  });
  await check('REAL sign-out stops playback and revokes loaded private object URLs',async()=>{
    await page.goto(base+`/app/recordings/${record.id}`);await readyPlayers(page);
    await page.getByRole('button',{name:'Play Heart',exact:true}).click();await page.getByRole('button',{name:'Pause Heart',exact:true}).waitFor();
    const before=await page.evaluate(()=>window.__frostUrls);assert.equal(before.created,3);
    await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.waitForURL(url=>url.pathname==='/login');
    assert.equal(await page.locator('.sf-player,.sf-signal-chart').count(),0);
    const after=await page.evaluate(()=>window.__frostUrls);assert.equal(after.revoked,after.created);
    await signIn(page,'alice');
  });
  await check('FAKE MICROPHONE, REAL AudioWorklet/PCM upload, original stored sample rate is not device-resampled analysis',async()=>{
    await page.goto(base+'/app/recordings/new/record');await page.getByRole('button',{name:'Start recording',exact:true}).click();
    await page.getByRole('button',{name:'Stop recording',exact:true}).waitFor();await page.waitForFunction(()=>/Recording · [1-9]/.test(document.body.innerText));
    await page.getByRole('button',{name:'Stop recording',exact:true}).click();await page.getByRole('button',{name:'Save recording',exact:true}).waitFor();
    await page.getByLabel('Recording title',{exact:true}).fill('Synthetic device capture — fake microphone, not hardware qualification');
    await readyPlayers(page,1);await shot('15-device-capture-review.png',page);
    await page.getByRole('button',{name:'Save recording',exact:true}).click();
    await page.waitForURL(url=>/^\/app\/recordings\/[^/]+$/.test(url.pathname));
    await page.getByRole('heading',{name:'Synthetic device capture — fake microphone, not hardware qualification',exact:true}).waitFor();
    await readyPlayers(page,1);
    const captured=(await(await fetch(api+'/api/recordings',{headers:headers('alice')})).json()).items.find(r=>r.title.startsWith('Synthetic device capture'));
    assert(captured);assert(captured.duration_sec>=1);assert.equal(captured.channels,1);
    assert.match(await page.locator('.sf-analysis-panel .sf-subtle').innerText(),new RegExp(captured.sample_rate_hz.toLocaleString()+' Hz stored WAV'));
  });
  await check('REAL durable failed job presentation; TEST-ONLY inference exception, no fallback/retry claim',async()=>{
    const candidate=(await(await fetch(api+'/api/recordings',{headers:headers('alice')})).json()).items.find(r=>r.title==='Synthetic reference 2');
    await page.goto(base+`/app/recordings/${candidate.id}`);await readyPlayers(page,1);await page.getByRole('button',{name:'Separate',exact:true}).click();
    await page.getByRole('heading',{name:'Waiting to separate',exact:true}).waitFor();
    worker=spawn(python,[fixture,'--worker'],{cwd:root,env:{...process.env,STETHOFUSE_M1_DATABASE:info.database,STETHOFUSE_M1_PRIVATE_STORAGE:info.privateStorage,STETHOFUSE_MODEL_CHECKPOINT:checkpoint},stdio:['pipe','pipe','pipe']});
    const finished=exit(worker);worker.stderr.on('data',d=>workerLog+=d);
    await new Promise((resolve,reject)=>{let text='';worker.stdout.on('data',d=>{text+=d;workerLog+=d;if(text.includes('READY_FOR_INFERENCE'))resolve();});worker.once('exit',code=>reject(new Error(`Failure fixture exit ${code}`)));setTimeout(()=>reject(new Error('Failure fixture timeout')),20000).unref();});
    worker.stdin.end('test-failure\n');await finished;worker=null;
    await page.getByRole('heading',{name:'Separation needs attention',exact:true}).waitFor();await readyPlayers(page,1);
    assert(await page.getByRole('button',{name:'Separate',exact:true}).isDisabled());
    assert.equal(await page.getByRole('button',{name:'Play Heart',exact:true}).count(),0);await shot('16-failed-job.png',page);
  });
  await check('PURE browser signal checks: supported PCM8/extensible PCM, silence has unavailable crest, malformed WAV fails',async()=>{
    const checks=await page.evaluate(async()=>{
      const {decodeWav,measureSignal}=await import('/src/frost/signal.ts');
      const signal={samples:new Float32Array(1000),rate:1000,channels:1,duration:1};
      const metrics=measureSignal(signal),bytes=new ArrayBuffer(1044),v=new DataView(bytes);
      const text=(at,s)=>{for(let i=0;i<s.length;i++)v.setUint8(at+i,s.charCodeAt(i));};
      text(0,'RIFF');v.setUint32(4,1036,true);text(8,'WAVEfmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,1000,true);v.setUint32(28,1000,true);v.setUint16(32,1,true);v.setUint16(34,8,true);text(36,'data');v.setUint32(40,1000,true);new Uint8Array(bytes,44).fill(128);
      const decoded=await decodeWav(new Blob([bytes]));
      const extended=new ArrayBuffer(1068),x=new DataView(extended);
      new Uint8Array(extended).set(new Uint8Array(bytes,0,36));
      x.setUint32(4,1060,true);x.setUint32(16,40,true);x.setUint16(20,0xfffe,true);
      x.setUint16(36,22,true);x.setUint16(38,8,true);x.setUint32(40,1,true);
      new Uint8Array(extended,44,16).set([1,0,0,0,0,0,16,0,128,0,0,170,0,56,155,113]);
      new Uint8Array(extended,60).set(new Uint8Array(bytes,36));
      const extensible=await decodeWav(new Blob([extended]));
      let rejected=false;try{await decodeWav(new Blob([new Uint8Array(20)]));}catch{rejected=true;}
      return {metrics,rate:decoded.rate,length:decoded.samples.length,allZero:decoded.samples.every(x=>x===0),extensibleLength:extensible.samples.length,rejected};
    });
    assert.equal(checks.metrics.lowLevel,true);assert.equal(checks.metrics.crestDb,null);assert.equal(checks.rate,1000);assert.equal(checks.extensibleLength,1000);assert(checks.allZero&&checks.rejected);
  });
  await check('REAL API stopped -> truthful unavailable state, no preview fallback',async()=>{
    await page.goto(base+'/app/library');await page.getByRole('button',{name:'Next page'}).waitFor();
    await stop(apiServer);await page.getByRole('button',{name:'Refresh access',exact:true}).click();await page.getByText('The request could not be completed. Please retry.',{exact:true}).waitFor();
    assert.equal(await page.locator('.sf-recordings li').count(),0);await shot('14-service-unavailable.png',page);
  });
  await check('No page exceptions, no preview assets/fixtures in live routes, no leaked audio after sign-out',async()=>{
    assert.deepEqual(errors,[]);assert(!traffic.some(r=>/fixtures|ux-preview/.test(r.path)));
    await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.waitForURL(url=>url.pathname==='/login');
    assert.equal(await page.locator('.sf-player,.sf-signal-chart').count(),0);
    const counts=await page.evaluate(()=>window.__frostUrls);assert(counts.revoked>=counts.created);
  });
}catch(error){
  process.exitCode=1;console.error(error.stack);
  const p=browser?.contexts().flatMap(c=>c.pages()).at(-1);if(p)await p.screenshot({path:path.join(output,'failure.png'),fullPage:true}).catch(()=>{});
}finally{
  if(worker)await stop(worker);if(browser)await browser.close();await stop(vite);await stop(apiServer);
  await writeFile(path.join(output,'results.json'),JSON.stringify({scope:layoutOnly?'LOCAL layout-only: REAL isolated API with empty authorized Library, test SDK/verifier identity. No worker/inference.':'LOCAL synthetic M0001.wav; existing test-only Firebase SDK/verifier stand-in, REAL API/proxy/SQLite/private storage/frozen worker. Not Firebase/emulator/production/physical hardware qualification.',startedAt,endedAt:new Date().toISOString(),isolation:info,checkpointSha256:expectedCheckpoint,specSha256:expectedSpec,fixtureSha256:hash(wav),checks,errors,screenshots,record,job,result,workerReceipt,traffic,serverLog,workerLog,frontendLog},null,2));
}

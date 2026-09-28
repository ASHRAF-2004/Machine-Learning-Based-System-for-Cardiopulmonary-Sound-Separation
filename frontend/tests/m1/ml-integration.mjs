// Synthetic PCM + actual frozen CPU worker/API/database; fictional Firebase identities only.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {access,mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
const base=process.env.FRONTEND_URL||'http://127.0.0.1:4191';
const root=path.resolve('..'),python=path.join(root,'.local/ml-integration/venv/bin/python');
const output=path.resolve(process.env.EVIDENCE_ROOT||'output/playwright/ml-integration-v1');
const checkpoint=process.env.STETHOFUSE_TEST_CHECKPOINT;
if(!checkpoint)throw new Error('Explicit frozen checkpoint path required');
try{await access(output);throw new Error('Evidence already exists');}catch(e){if(e.code!=='ENOENT')throw e;}
await mkdir(output,{recursive:true});
const n=60000,wav=Buffer.alloc(44+2*n);wav.write('RIFF');wav.writeUInt32LE(36+2*n,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(4000,24);wav.writeUInt32LE(8000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(2*n,40);
for(let i=0;i<n;i++)wav.writeInt16LE(Math.round(7000*Math.sin(2*Math.PI*75*i/4000)+1800*Math.sin(2*Math.PI*430*i/4000)),44+2*i);
const microphone=path.join(output,'synthetic-microphone.wav');await writeFile(microphone,wav);
const fixture=new URL('./ml_fixture.py',import.meta.url).pathname;
const apiServer=spawn(python,[fixture],{cwd:root,stdio:['ignore','pipe','pipe']});
let serverLog='',worker;apiServer.stderr.on('data',d=>serverLog+=d);
const checks=[],errors=[];let browser;
const check=async(name,fn)=>{try{await fn();checks.push({name,result:'PASS'});}catch(error){checks.push({name,result:'FAIL',error:error.message});throw error;}};
const waitExit=child=>new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',code=>code===0?resolve():reject(new Error(`Process exited ${code}`)));});
try{
 const info=await new Promise((resolve,reject)=>{let text='';apiServer.stdout.on('data',d=>{text+=d;if(text.includes('\n'))resolve(JSON.parse(text.split('\n')[0]));});apiServer.once('exit',code=>reject(new Error(`API fixture exited ${code}`)));setTimeout(()=>reject(new Error('API timeout')),15000).unref();});
 const api=`http://127.0.0.1:${info.port}`,headers=uid=>({Authorization:`Bearer M1-MOCK:${uid}`});
 for(let i=0;i<80;i++){try{if((await fetch(api+'/health')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 const workerEnv={...process.env,STETHOFUSE_M1_DATABASE:info.database,STETHOFUSE_M1_PRIVATE_STORAGE:info.privateStorage,STETHOFUSE_MODEL_CHECKPOINT:checkpoint};
 browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',`--use-file-for-fake-audio-capture=${microphone}`]});
 const context=await browser.newContext({viewport:{width:1366,height:1000},reducedMotion:'reduce',permissions:['microphone']});
 await context.route('**/node_modules/.vite/deps/firebase_app.js*',r=>r.fulfill({contentType:'application/javascript',path:new URL('./mock-firebase-app.mjs',import.meta.url).pathname}));
 await context.route('**/node_modules/.vite/deps/firebase_auth.js*',r=>r.fulfill({contentType:'application/javascript',path:new URL('./mock-firebase-auth.mjs',import.meta.url).pathname}));
 await context.route('**/src/config/runtime.ts*',r=>r.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
 await context.route('**/api/**',async route=>{const response=await route.fetch({url:api+new URL(route.request().url()).pathname,headers:{...route.request().headers(),host:`127.0.0.1:${info.port}`},maxRedirects:0});await route.fulfill({response});});
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 const signIn=async uid=>{await page.goto(base+'/login');await page.getByRole('textbox',{name:'Email address',exact:true}).fill(uid+'@example.invalid');await page.getByLabel('Password',{exact:true}).fill('Fictional-local-only');await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.locator('[data-live-workspace=true]').waitFor();};
 let record,job,result;
 await check('Owner upload, metadata review and one asynchronous Separate action',async()=>{
  await signIn('alice');await page.goto(base+'/app/recordings/new/upload');await page.locator('input[type=file]').setInputFiles({name:'generated-15s.wav',mimeType:'audio/wav',buffer:wav});await page.getByLabel('Recording title',{exact:true}).fill('Synthetic integration input');await page.getByRole('button',{name:'Upload recording',exact:true}).click();await page.getByRole('heading',{name:'Synthetic integration input',exact:true}).waitFor();
  record=(await(await fetch(api+'/api/recordings',{headers:headers('alice')})).json()).items[0];
  await page.getByRole('button',{name:'Separate',exact:true}).click();await page.getByText('Waiting for the processing worker.',{exact:true}).waitFor();
  job=(await(await fetch(api+'/api/jobs',{headers:headers('alice')})).json()).items[0];assert.equal(job.status,'queued');
  await page.screenshot({path:path.join(output,'queued.png'),fullPage:true});
 });
 await check('Durable worker processing is visible, then real result becomes ready',async()=>{
  worker=spawn(python,[fixture,'--worker'],{cwd:root,env:workerEnv,stdio:['pipe','pipe','pipe']});
  const exit=waitExit(worker);
  await new Promise((resolve,reject)=>{let text='';worker.stdout.on('data',d=>{text+=d;if(text.includes('READY_FOR_INFERENCE'))resolve();});worker.once('exit',code=>reject(new Error(`Worker exited early ${code}`)));setTimeout(()=>reject(new Error('Worker startup timeout')),20000).unref();});
  await page.getByText('Separating heart and lung sounds.',{exact:true}).waitFor();await page.screenshot({path:path.join(output,'processing.png'),fullPage:true});
  worker.stdin.end('continue\n');await exit;worker=null;
  await page.getByRole('link',{name:'Review result',exact:true}).waitFor();await page.getByRole('link',{name:'Review result',exact:true}).click();await page.getByRole('heading',{name:'Separation result',exact:true}).waitFor();
  result=(await(await fetch(api+'/api/results',{headers:headers('alice')})).json()).items[0];assert.equal(result.provenance.output_samples,60000);
 });
 await check('Both private float WAV outputs play with exact 15-second duration; refresh persists result',async()=>{
  for(const section of await page.locator('.audio-track').all()){await section.getByRole('button',{name:'Load authorized file',exact:true}).click();await section.locator('audio').waitFor();}
  await page.waitForFunction(()=>[...document.querySelectorAll('audio')].length===2&&[...document.querySelectorAll('audio')].every(a=>Number.isFinite(a.duration)));
  assert.deepEqual(await page.locator('audio').evaluateAll(nodes=>nodes.map(a=>a.duration)),[15,15]);
  assert.equal((await fetch(api+result.resources[0].url)).status,401);
  await page.screenshot({path:path.join(output,'ready-heart-lung.png'),fullPage:true});await page.reload();await page.getByRole('heading',{name:'Separation result',exact:true}).waitFor();
  assert.equal(await page.getByRole('combobox').count(),0);
 });
 await check('Real device-capture UI encodes synthetic microphone PCM and privately uploads it',async()=>{
  await page.goto(base+'/app/recordings/new/record');await page.getByRole('button',{name:'Start recording',exact:true}).click();await page.getByRole('button',{name:'Stop recording',exact:true}).waitFor();await page.waitForFunction(()=>/Recording · [1-9]/.test(document.body.innerText));await page.getByRole('button',{name:'Stop recording',exact:true}).click();await page.getByRole('button',{name:'Save recording',exact:true}).waitFor();await page.getByLabel('Recording title',{exact:true}).fill('Synthetic device capture');await page.getByRole('button',{name:'Save recording',exact:true}).click();await page.getByRole('heading',{name:'Synthetic device capture',exact:true}).waitFor();
  const capture=(await(await fetch(api+'/api/recordings',{headers:headers('alice')})).json()).items.find(r=>r.title==='Synthetic device capture');assert(capture.duration_sec>=1);assert.equal(capture.channels,1);
 });
 await check('Assigned analyst sees only explicitly shared output; revocation blocks subsequent review',async()=>{
  const grant=async(permission,resource_id)=>(await fetch(api+`/api/recordings/${record.id}/grants`,{method:'POST',headers:{...headers('alice'),'Content-Type':'application/json'},body:JSON.stringify({recipient_id:info.analystId,permission,resource_id})})).json();
  const assignment=await grant('review',result.id);for(const r of result.resources)await grant('read',r.id);
  await page.getByRole('button',{name:/alice@example.invalid/}).click();await page.getByRole('menuitem',{name:'Sign out',exact:true}).click();await page.waitForURL(url=>url.pathname==='/login');await signIn('analyst');await page.goto(base+`/app/reviews/${assignment.id}`);await page.getByRole('heading',{name:'Assigned review',exact:true}).waitFor();await page.getByRole('heading',{name:'Separation result',exact:true}).waitFor();assert.equal(await page.locator('.audio-track').count(),2);
  assert.equal((await fetch(api+record.resources[0].url,{headers:headers('analyst')})).status,403);
  await fetch(api+`/api/recordings/${record.id}/revoke-access`,{method:'POST',headers:{...headers('alice'),'Content-Type':'application/json'},body:JSON.stringify({recipient_id:info.analystId,confirmed_recording_id:record.id})});await page.reload();await page.getByText('You do not have permission for this action or resource.',{exact:true}).waitFor();assert.equal(await page.locator('audio').count(),0);
  assert.deepEqual(errors,[]);
 });
}finally{
 if(worker)worker.kill('SIGKILL');if(browser)await browser.close();apiServer.kill('SIGTERM');
 await new Promise(resolve=>{if(apiServer.exitCode!==null)return resolve();apiServer.once('exit',resolve);setTimeout(()=>{apiServer.kill('SIGKILL');resolve();},5000).unref();});
 await writeFile(path.join(output,'results.json'),JSON.stringify({scope:'LOCAL only; synthetic audio/fake microphone; fictional identity; real M1 API, database, private files and frozen v2 CPU inference. No T9 or production.',checks,errors,serverLog},null,2));
}

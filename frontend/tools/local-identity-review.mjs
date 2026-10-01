// Isolated persistent LOCAL review. Identity provider alone uses the approved test seam.
// Real API/SQLite/files/worker; no production connection, fixtures or API interception.
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createServer} from 'node:net';
import {fileURLToPath} from 'node:url';
import {cp,mkdir,open,readFile,writeFile,stat} from 'node:fs/promises';
import path from 'node:path';
import {chromium} from 'playwright-core';

const filename=fileURLToPath(import.meta.url),frontend=path.resolve(path.dirname(filename),'..');
const sharingReview=process.argv.includes('--sharing-review');
const root=path.resolve(frontend,'..'),review=path.join(root,sharingReview?'.local/handle-sharing-review':'.local/identity-review');
const source=path.join(root,sharingReview?'.local/identity-review':'.local/manual-review');
const database=path.join(review,'data/review.sqlite3'),storage=path.join(review,'private');
const python=path.join(root,'.local/ml-integration/venv/bin/python');
const frontendPort=sharingReview?4198:4197,apiPort=sharingReview?8198:8197;
const url=`http://127.0.0.1:${frontendPort}`,api=`http://127.0.0.1:${apiPort}`,receipt=path.join(review,'session.json');
const reviewLabel=sharingReview?'LOCAL SHARING REVIEW':'LOCAL IDENTITY REVIEW';
const restartCommand=`node ${filename}${sharingReview?' --sharing-review':''}`;
const checkpoint=path.join(root,'.local/training/stethofuse-tcn-v1/pre-t9-family-refit-v1/refit-all-nontest-seed20260928/checkpoints/endpoint.pt');
const spec=path.join(root,'research/configs/final_separator_v2.json');
const hashes={checkpoint:'1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658',spec:'2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b'};
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function birth(pid){const value=await readFile(`/proc/${pid}/stat`,'utf8');return value.slice(value.lastIndexOf(')')+2).split(' ')[19];}
if(process.argv.includes('--stop')){
  let state;try{state=JSON.parse(await readFile(receipt,'utf8'));}catch(error){if(error.code==='ENOENT'){console.log('No identity-review session; data retained.');process.exit(0);}throw error;}
  try{if(await birth(state.pid)!==state.processBirth||!(await readFile(`/proc/${state.pid}/cmdline`,'utf8')).split('\0').includes(filename))throw Error('PID identity mismatch; refusing to signal.');process.kill(state.pid,'SIGTERM');console.log('Stop requested for identity review only. All review data is retained.');}
  catch(error){if(!['ENOENT','ESRCH'].includes(error.code))throw error;console.log('Session already stopped; data retained.');}
  process.exit(0);
}
process.umask(0o077);
for(const directory of [review,path.dirname(database)]){await mkdir(directory,{recursive:true,mode:0o700});if((await stat(directory)).mode&0o077)throw Error('Review directory permissions are not private.');}
for(const item of [database,storage,database+'.worker.lock'])if(!item.startsWith(review+'/'))throw Error('Local path isolation failed.');
if(digest(await readFile(checkpoint))!==hashes.checkpoint||digest(await readFile(spec))!==hashes.spec)throw Error('Frozen artifact mismatch; startup refused.');
for(const port of [frontendPort,apiPort])await new Promise((resolve,reject)=>{const server=createServer();server.once('error',reject);server.listen(port,'127.0.0.1',()=>server.close(resolve));});
// Snapshot through SQLite's backup API, read-only at the source. Never overwrite a DB.
let existing=true;try{await stat(database);}catch(error){if(error.code==='ENOENT')existing=false;else throw error;}
if(!existing){
  await stat(path.join(source,'data/review.sqlite3'));
  const reserved=await open(database,'wx',0o600);await reserved.close();
  await new Promise((resolve,reject)=>{const child=spawn(python,['-c',"import sqlite3,sys; source=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True); target=sqlite3.connect(sys.argv[2]); source.backup(target); target.close(); source.close()",path.join(source,'data/review.sqlite3'),database],{stdio:'inherit'});child.once('error',reject);child.once('exit',code=>code===0?resolve():reject(Error('Read-only review snapshot failed.')));});
  await cp(path.join(source,'private'),storage,{recursive:true,errorOnExist:true,force:false});
}else await stat(storage);
if((await stat(storage)).mode&0o077)throw Error('Private storage permissions are not private.');
await new Promise((resolve,reject)=>{const child=spawn(python,['-c',"import sqlite3,sys; db=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True); active=db.execute(\"SELECT COUNT(*) FROM m1_jobs WHERE status IN ('queued','processing')\").fetchone()[0]; db.close(); assert active==0, 'Review has unfinished jobs; refusing automatic processing during identity setup'",database],{stdio:'inherit'});child.once('error',reject);child.once('exit',code=>code===0?resolve():reject(Error('Review job-state preflight failed.')));});
const manifest=JSON.parse(await readFile(path.join(root,'research/manifests/hls_native_triplets_v1.json'),'utf8'));
const raw=manifest.rows.find(item=>item.triplet_id==='M0001');
if(!raw?.eligible_non_test||raw.exclusion_reasons.length)throw Error('M0001 is not verified eligible non-test data.');
await mkdir(path.join(review,'raw-hls'),{recursive:true,mode:0o700});
const fixture=path.join(review,'raw-hls/M0001.wav');
try{await cp(path.join(root,raw.files.mixture.path),fixture,{errorOnExist:true,force:false});}catch(error){if(error.code!=='ERR_FS_CP_EEXIST')throw error;}
if(digest(await readFile(fixture))!==raw.files.mixture.sha256)throw Error('Review fixture mismatch; existing bytes preserved.');
const children=[];let browser,stopping=false;
const state={pid:process.pid,processBirth:await birth(process.pid),status:'starting',url,api,database,privateStorage:storage,workerLock:database+'.worker.lock',fixture,startedAt:new Date().toISOString(),identityMode:'TEST ONLY fixed verifier/SDK; fictional Alice, healthcare_staff',checkpointSha256:hashes.checkpoint,specSha256:hashes.spec};
async function save(){await writeFile(receipt,JSON.stringify(state,null,2)+'\n');}
async function stopChild(child){if(child.exitCode!==null||child.signalCode!==null)return;await new Promise(resolve=>{child.once('exit',resolve);child.kill('SIGTERM');});}
async function shutdown(reason,code=0){if(stopping)return;stopping=true;console.log(`Stopping ONLY identity review (${reason}). Data retained.`);if(browser)await browser.close().catch(()=>{});for(const child of children.slice().reverse())await stopChild(child.process);state.status='stopped';state.stoppedAt=new Date().toISOString();await save();process.exit(code);}
process.once('SIGINT',()=>void shutdown('Ctrl+C'));process.once('SIGTERM',()=>void shutdown('targeted stop'));
function start(name,args,cwd,env){const child=spawn(args[0],args.slice(1),{cwd,env,stdio:['ignore','pipe','pipe']});const item={name,process:child,log:''};children.push(item);const log=bytes=>{item.log+=bytes;process.stdout.write(`[${name}] ${bytes}`);};child.stdout.on('data',log);child.stderr.on('data',log);child.once('error',error=>{console.error(error.message);void shutdown('startup failure',1);});child.once('exit',()=>{if(!stopping)void shutdown(name+' exited',1);});state[name+'Pid']=child.pid;return item;}
async function health(address){for(let i=0;i<120;i++){try{if((await fetch(address,{signal:AbortSignal.timeout(1000)})).ok)return;}catch{}await delay(100);}throw Error('Local health timeout: '+address);}
try{
  console.log(`${reviewLabel} — no real credentials.\nFrontend ${url}\nAPI ${api}\nDB ${database}\nStorage ${storage}`);
  start('api',[python,path.join(frontend,'tools/identity_review_api.py'),...(sharingReview?['--sharing-review']:[])],root,{...process.env,PYTHONUNBUFFERED:'1'});await health(api+'/health');
  start('frontend',[process.execPath,path.join(frontend,'node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',String(frontendPort),'--strictPort'],frontend,{...process.env,STETHOFUSE_API_PROXY:api});await health(url);
  const worker=start('worker',[python,'-m','app.m1.worker'],root,{...process.env,PYTHONUNBUFFERED:'1',STETHOFUSE_M1_DATABASE:database,STETHOFUSE_M1_PRIVATE_STORAGE:storage,STETHOFUSE_SEPARATION_ENABLED:'1',STETHOFUSE_MODEL_CHECKPOINT:checkpoint,STETHOFUSE_SEPARATOR_SPEC:spec});
  for(let i=0;i<200&&!worker.log.includes('"status": "ready"');i++)await delay(100);
  if(!worker.log.includes('"status": "ready"'))throw Error('Frozen CPU worker did not become ready.');
  state.workerReady=JSON.parse(worker.log.split('\n').find(line=>line.includes('"status": "ready"')));
  browser=await chromium.launchPersistentContext(path.join(review,'browser-profile'),{executablePath:'/usr/bin/google-chrome',headless:false,viewport:null,acceptDownloads:true,args:['--window-size=1440,900']});
  await browser.route('**/node_modules/.vite/deps/firebase_app.js*',r=>r.fulfill({contentType:'application/javascript',path:path.join(frontend,'tests/m1/mock-firebase-app.mjs')}));
  await browser.route('**/node_modules/.vite/deps/firebase_auth.js*',r=>r.fulfill({contentType:'application/javascript',path:path.join(frontend,'tests/m1/mock-firebase-auth.mjs')}));
  await browser.route('**/src/config/runtime.ts*',r=>r.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
  await browser.addInitScript(({origin,mode})=>{if(location.origin===origin){if(!sessionStorage.getItem('__identity_review_seeded')){sessionStorage.setItem('__m1_test_identity',JSON.stringify({uid:'alice',verified:true}));sessionStorage.setItem('__identity_review_seeded','1');}document.addEventListener('DOMContentLoaded',()=>{const label=document.createElement('div');label.id='local-identity-review-mode';label.setAttribute('role','note');label.textContent=mode+' · Fictional test identity · No real credentials';label.style.cssText='position:fixed;bottom:8px;right:12px;z-index:9999;max-width:calc(100vw - 24px);padding:6px 12px;border:1px solid #739483;border-radius:6px;background:#173e32;color:#fff;font:12px/1.4 sans-serif;pointer-events:none;';document.body.append(label);});}},{origin:url,mode:reviewLabel});
  await browser.route(value=>['http:','https:'].includes(value.protocol)&&value.origin!==url,r=>r.abort());
  const page=browser.pages()[0]||await browser.newPage();await page.goto(url+'/app/profile');await page.getByRole('heading',{name:'Your profile',exact:true}).waitFor();await page.bringToFront();await page.screenshot({path:path.join(review,'setup.png')});
  state.status='ready';state.readyAt=new Date().toISOString();await save();
  console.log(`READY — keep this terminal open. No automated owner interaction.\nStop: ${restartCommand} --stop\nRestart: ${restartCommand}`);
  browser.once('close',()=>{if(!stopping)void shutdown('browser closed');});await new Promise(()=>{});
}catch(error){console.error(error.message);await shutdown('setup failed',1);}

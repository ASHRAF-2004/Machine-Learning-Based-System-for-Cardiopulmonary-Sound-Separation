// MOCK IDENTITY + REAL LOCAL API/SQLITE/FILES + actual browser UI. Not Firebase verification.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {access,mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
const base=process.env.FRONTEND_URL||'http://127.0.0.1:4180';
const output=path.resolve(process.env.EVIDENCE_ROOT||'output/playwright/m1/cross-layer');
try{await access(output);throw new Error('Refusing to overwrite evidence.');}catch(e){if(e.code!=='ENOENT')throw e;}
await mkdir(output,{recursive:true});
const python=process.env.M1_TEST_PYTHON||'/home/ashraf/Documents/StethoFuse/.local/venvs/backend-smoke/bin/python';
const server=spawn(python,[new URL('./api_fixture.py',import.meta.url).pathname],{stdio:['ignore','pipe','pipe']});
let logs='';server.stderr.on('data',data=>{logs+=data.toString();});
const checks=[],errors=[];let browser;
const check=async(name,run)=>{try{await run();checks.push({name,result:'PASS'});}catch(e){checks.push({name,result:'FAIL',error:e.message});throw e;}};
try{
 const port=await new Promise((resolve,reject)=>{let text='';server.stdout.on('data',data=>{text+=data;if(text.includes('\n')){try{resolve(JSON.parse(text.split('\n')[0]).port);}catch(e){reject(e);}}});server.on('exit',code=>reject(new Error(`Fixture exited ${code}: ${logs}`)));setTimeout(()=>reject(new Error('Fixture startup timeout')),10000).unref();});
 const api=`http://127.0.0.1:${port}`;
 for(let i=0;i<50;i++){try{if((await fetch(api+'/health')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1536,height:1024},reducedMotion:'reduce'});
 await context.route('**/node_modules/.vite/deps/firebase_app.js*',route=>route.fulfill({contentType:'application/javascript',path:new URL('./mock-firebase-app.mjs',import.meta.url).pathname}));
 await context.route('**/node_modules/.vite/deps/firebase_auth.js*',route=>route.fulfill({contentType:'application/javascript',path:new URL('./mock-firebase-auth.mjs',import.meta.url).pathname}));
 await context.route('**/src/config/runtime.ts*',route=>route.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
 await context.route('**/api/**',async route=>{
  const request=route.request();
  const response=await route.fetch({url:api+new URL(request.url()).pathname,headers:{...request.headers(),host:`127.0.0.1:${port}`},maxRedirects:0});
  await route.fulfill({response});
 });
 const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
 const signIn=async uid=>{await page.goto(base+'/login');await page.getByRole('textbox',{name:'Email address',exact:true}).fill(uid+'@example.invalid');await page.getByLabel('Password',{exact:true}).fill('Fictional-test-password26');await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.locator('[data-live-workspace=true]').waitFor();};
 const headers=uid=>({Authorization:`Bearer M1-MOCK:${uid}`});
 let record;
 await check('MOCK identity creates a default-staff account through the REAL API',async()=>{await signIn('alice');const user=await(await fetch(api+'/api/auth/me',{headers:headers('alice')})).json();assert.equal(user.user.role,'healthcare_staff');assert.equal(user.user.uid,'alice');});
 await check('Browser upload persists actual WAV under server-derived ownership',async()=>{
  const wav=Buffer.alloc(844);wav.write('RIFF');wav.writeUInt32LE(836,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(4000,24);wav.writeUInt32LE(8000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(800,40);
  await page.goto(base+'/app/recordings/new/upload');await page.locator('input[type=file]').setInputFiles({name:'fictional.wav',mimeType:'audio/wav',buffer:wav});await page.getByLabel('Recording title',{exact:true}).fill('Cross-layer fictional WAV');await page.getByRole('button',{name:'Upload recording',exact:true}).click();await page.getByRole('heading',{name:'Cross-layer fictional WAV',exact:true}).waitFor();
  record=(await(await fetch(api+'/api/recordings',{headers:headers('alice')})).json()).items[0];assert.equal(record.file_size_bytes,844);assert.equal(record.is_owner,true);
 });
 await check('Authorized browser media loads from real protected bytes; unauthenticated direct access denied',async()=>{await page.getByRole('button',{name:'Load authorized file',exact:true}).click();await page.locator('audio[src^="blob:"]').waitFor();assert.equal((await fetch(api+record.resources[0].url)).status,401);await page.screenshot({path:path.join(output,'real-api-owned-recording.png'),fullPage:true});});
 await check('Refresh retains the uploaded record via current identity and real SQLite',async()=>{await page.reload();await page.getByRole('heading',{name:'Cross-layer fictional WAV',exact:true}).waitFor();});
 await check('Logout removes loaded media and a second account cannot retrieve owner data',async()=>{
  await page.getByRole('button',{name:/alice@example.invalid/}).click();await page.getByRole('menuitem',{name:'Sign out',exact:true}).click();await page.waitForURL(url=>url.pathname==='/login');await page.getByRole('textbox',{name:'Email address',exact:true}).waitFor();assert.equal(await page.locator('audio').count(),0);await signIn('bob');
  assert.deepEqual((await(await fetch(api+'/api/recordings',{headers:headers('bob')})).json()).items,[]);assert.equal((await fetch(api+record.resources[0].url,{headers:headers('bob')})).status,403);
  await page.goto(base+`/app/recordings/${record.id}`);await page.getByText('You do not have permission for this action or resource.',{exact:true}).waitFor();assert.equal(await page.locator('audio').count(),0);await page.screenshot({path:path.join(output,'real-api-cross-account-denial.png'),fullPage:true});
 });
 await check('Normal account admin request denied by real API; no JS errors',async()=>{assert.equal((await fetch(api+'/api/admin/users',{headers:headers('bob')})).status,403);assert.deepEqual(errors,[]);});
}finally{
 if(browser)await browser.close();server.kill('SIGTERM');
 await new Promise(resolve=>{if(server.exitCode!==null)return resolve();server.once('exit',resolve);setTimeout(()=>{server.kill('SIGKILL');resolve();},5000).unref();});
 await writeFile(path.join(output,'results.json'),JSON.stringify({testedAt:new Date().toISOString(),scope:'MOCK SDK/verified identity; real local FastAPI, SQLite, upload and protected file delivery. No live Firebase/emulator/production.',checks,errors,serverDiagnostic:logs},null,2));
}

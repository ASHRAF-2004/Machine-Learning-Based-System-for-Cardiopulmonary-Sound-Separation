// Focused LOCAL review: real existing raw HLS artifacts; mocked status/denial cases are labelled.
// Read-only against the owner's review API. No upload, job creation, training or T9 access.
import {chromium} from 'playwright-core';
import {decodeWav,measureSignal} from '../src/frost/signal.ts';
import assert from 'node:assert/strict';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';

const base=process.env.FRONTEND_URL||'http://127.0.0.1:4196';
assert.match(base,/^http:\/\/127\.0\.0\.1:4196$/,'Only the isolated manual-review service is approved.');
const output=path.resolve(process.env.EVIDENCE_ROOT||'output/playwright/owner-feedback/v1');
await mkdir(output,{recursive:true});
const headers={Authorization:'Bearer M1-MOCK:alice'};
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
async function get(endpoint){const response=await fetch(base+'/api'+endpoint,{headers});assert.equal(response.status,200);return response.json();}
const [records,jobs,results]=await Promise.all([get('/recordings'),get('/jobs'),get('/results')]);
const rawSha='8e0efd28aaf89f7efbd8107805a74bd837bcc70ea3dc4b4b783eff0e6a220616';
const result=results.items.find(item=>item.provenance?.input_artifact_sha256===rawSha);
assert(result,'An existing completed raw HLS M0001 result is required; never create a substitute.');
const record=records.items.find(item=>item.id===result.recording_id);
const job=jobs.items.find(item=>item.id===result.job_id);
assert(record&&job&&job.status==='succeeded');
const registry=JSON.parse(await readFile('../research/manifests/hls_native_triplets_v1.json','utf8'));
assert(registry.rows.some(row=>row.triplet_id==='M0001'&&row.eligible_non_test&&row.files.mixture.sha256===rawSha));
const expected={};
const ids={};
for(const kind of ['original','heart','lung']){
  const resource=record.resources.find(item=>item.kind===kind+'_audio');assert(resource);ids[kind]=resource.id;
  const response=await fetch(base+'/api/media/'+resource.id,{headers});assert.equal(response.status,200);
  const bytes=Buffer.from(await response.arrayBuffer());if(kind==='original')assert.equal(digest(bytes),rawSha);
  const signal=await decodeWav(new Blob([bytes]));expected[kind]={...measureSignal(signal),duration:signal.duration,sha256:digest(bytes)};
}
const report={scope:'LOCAL real read-only raw HLS artifacts; TEST ONLY SDK/verifier; status and denial cases MOCKED in a separate browser',recordingId:record.id,resultId:result.id,measurements:expected,checks:[],screenshots:[]};
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:900}});
const errors=[];context.on('page',page=>page.on('pageerror',error=>errors.push(error.message)));
await context.route('**/node_modules/.vite/deps/firebase_app.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-app.mjs')}));
await context.route('**/node_modules/.vite/deps/firebase_auth.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-auth.mjs')}));
await context.route('**/src/config/runtime.ts*',r=>r.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
await context.addInitScript(({origin})=>{if(location.origin===origin)sessionStorage.setItem('__m1_test_identity',JSON.stringify({uid:'alice',verified:true}));},{origin:base});
await context.route(url=>['http:','https:'].includes(url.protocol)&&url.origin!==base,r=>r.abort());
const page=await context.newPage();
async function check(name,fn){await fn();report.checks.push({name,status:'PASS'});console.log('PASS',name);}
async function shot(name,locator=page){await page.evaluate(()=>document.fonts.ready);await locator.screenshot({path:path.join(output,name)});report.screenshots.push(name);}
async function noOverflow(){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
try{
  await check('REAL raw HLS Original/Heart/Lung before-after values match unchanged artifact samples',async()=>{
    await page.goto(base+'/app/recordings/'+record.id);
    await page.waitForFunction(()=>document.querySelectorAll('.sf-player[data-media-state="ready"]').length===3);
    const table=page.locator('.sf-comparison-table');await table.waitFor();
    for(const [label,key,unit] of [['RMS level','rmsDb','dBFS'],['Peak level','peakDb','dBFS'],['Crest factor','crestDb','dB']]){
      const cells=await table.getByRole('row',{name:new RegExp('^'+label+' ')}).locator('td').allTextContents();
      assert.deepEqual(cells,['original','heart','lung'].map(kind=>expected[kind][key].toFixed(1)+' '+unit));
    }
    assert.match(await page.locator('.sf-comparison-guidance').innerText(),/not separation accuracy/);
    await noOverflow();await shot('01-before-after-frost-desktop.png',page.locator('.sf-comparison-panel'));
    await shot('02-ready-raw-detail-desktop.png');
  });
  await check('REAL playback 150/200 percent does not change measured comparison',async()=>{
    const before=await page.locator('.sf-comparison-table').innerText();
    const slider=page.getByRole('slider',{name:'Heart playback volume',exact:true});await slider.focus();await slider.press('Home');
    for(let i=0;i<30;i++)await slider.press('ArrowRight');
    assert.match(await slider.getAttribute('aria-valuetext'),/150 percent, boost enabled/);
    for(let i=0;i<10;i++)await slider.press('ArrowRight');
    assert.match(await slider.getAttribute('aria-valuetext'),/200 percent, boost enabled/);
    assert.equal(await page.locator('.sf-comparison-table').innerText(),before);
  });
  await check('REAL comparison Frost/Midnight and 390px mobile remain readable without horizontal overflow',async()=>{
    await page.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();
    await shot('03-before-after-midnight-desktop.png',page.locator('.sf-comparison-panel'));
    await page.setViewportSize({width:390,height:844});await noOverflow();
    await shot('04-before-after-midnight-mobile.png',page.locator('.sf-comparison-panel'));
    await page.getByRole('button',{name:'Switch to Frost theme',exact:true}).click();
    await page.setViewportSize({width:1440,height:900});
  });
  await check('REAL recording card and direct recording route are coming-soon; upload remains available',async()=>{
    await page.goto(base+'/app/recordings/new');
    await page.getByRole('heading',{name:'Record audio',exact:true}).waitFor();
    assert.equal(await page.getByRole('link',{name:'Record audio',exact:true}).count(),0);
    assert.equal(await page.getByRole('link',{name:'Upload WAV',exact:true}).count(),1);
    await page.waitForFunction(()=>document.querySelector('.sf-recording-lock img')?.complete);
    await shot('05-new-recording-coming-soon-desktop.png');
    await page.setViewportSize({width:390,height:844});await noOverflow();await shot('06-new-recording-coming-soon-mobile.png');
    await page.goto(base+'/app/recordings/new/record');await page.getByRole('heading',{name:'Live sound, a little later.'}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Start recording',exact:true}).count(),0);
    await page.setViewportSize({width:1440,height:900});
  });
  let phase='recorded',resolvePost;
  await context.route('**/api/recordings/'+record.id,r=>r.fulfill({json:{...record,resources:record.resources.filter(item=>item.kind==='original_audio')}}));
  await context.route('**/api/jobs',r=>r.fulfill({json:{items:jobs.items.filter(item=>item.recording_id!==record.id)}}));
  await context.route('**/api/results',r=>r.fulfill({json:{items:results.items.filter(item=>item.recording_id!==record.id)}}));
  await context.route('**/api/recordings/'+record.id+'/jobs',async r=>{assert.equal(r.request().method(),'POST');await new Promise(resolve=>resolvePost=resolve);await r.fulfill({status:202,json:{...job,status:'queued',result_id:null}});});
  await context.route('**/api/jobs/'+job.id,r=>r.fulfill({json:{...job,status:phase,result_id:null}}));
  await check('MOCK status: immediate request animation -> queued -> processing, with no fictitious percentage',async()=>{
    await page.goto(base+'/app/recordings/'+record.id);await page.getByRole('button',{name:'Separate',exact:true}).click();
    await page.getByRole('heading',{name:'Starting separation',exact:true}).waitFor();
    assert(await page.getByRole('button',{name:'Starting…',exact:true}).isDisabled());
    await shot('07-mock-requesting-desktop.png');
    phase='queued';resolvePost();await page.getByRole('heading',{name:'Waiting to separate',exact:true}).waitFor();
    assert(await page.getByRole('button',{name:'Queued…',exact:true}).isDisabled());
    phase='processing';await page.getByRole('heading',{name:'Separation in progress',exact:true}).waitFor();
    assert(await page.getByRole('button',{name:'Separating…',exact:true}).isDisabled());
    const progress=page.getByRole('region',{name:'Recording progress'});
    assert.equal(await progress.locator('.sf-working-wave i').count(),5);
    assert(!/\d+%/.test(await progress.innerText()));
    assert.notEqual(await progress.locator('.sf-working-wave i').first().evaluate(el=>getComputedStyle(el).animationName),'none');
    await shot('08-mock-processing-desktop.png');
    await page.emulateMedia({reducedMotion:'reduce'});
    assert.equal(await progress.locator('.sf-working-wave i').first().evaluate(el=>getComputedStyle(el).animationName),'none');
  });
  await context.unroute('**/api/recordings/'+record.id);
  await context.unroute('**/api/jobs');await context.unroute('**/api/results');
  await context.unroute('**/api/recordings/'+record.id+'/jobs');await context.unroute('**/api/jobs/'+job.id);
  await page.emulateMedia({reducedMotion:'no-preference'});
  await check('MOCK media revocation clears Heart comparison values without revealing denied audio',async()=>{
    await page.goto(base+'/app/recordings/'+record.id);
    await page.waitForFunction(()=>document.querySelectorAll('.sf-player[data-media-state="ready"]').length===3);
    await context.route('**/api/media/'+ids.heart,r=>r.fulfill({status:403,json:{detail:'Access denied'}}));
    await page.getByRole('button',{name:'Refresh access',exact:true}).click();
    await page.locator('.sf-player--heart[data-media-state="denied-or-error"]').waitFor();
    const cells=await page.locator('.sf-comparison-table td[data-source="heart"]').allTextContents();
    assert(cells.length===5&&cells.every(value=>value==='Unavailable'));
    await shot('09-mock-denied-heart-comparison.png',page.locator('.sf-comparison-panel'));
  });
  assert.deepEqual(errors,[]);report.consoleErrors=errors;report.status='PASS';
}catch(error){report.status='FAIL';report.error=error.message;throw error;}
finally{await writeFile(path.join(output,'receipt.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}

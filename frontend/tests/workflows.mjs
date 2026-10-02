import {chromium} from 'playwright-core';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

const base='http://127.0.0.1:4180';
const evidence=path.resolve(process.env.EVIDENCE_ROOT || 'evidence','workflows');
await mkdir(evidence,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
const page=await context.newPage();
const failures=[],passes=[],errors=[];
page.on('pageerror',error=>errors.push(error.message));
const check=async(name,action)=>{try{await action();passes.push(name);console.log(`PASS ${name}`);}catch(error){failures.push({name,error:error.message});console.log(`FAIL ${name}: ${error.message}`);await page.screenshot({path:path.join(evidence,`failure-${failures.length}.png`),fullPage:true});}};
const go=async(route)=>{await page.goto(base+route);await page.locator('h1').first().waitFor();};
const persona=async(id,route='/app/dashboard')=>{await page.evaluate(id=>sessionStorage.setItem('stethofuse-demo-persona',id),id);await go(route);};
await page.goto(base);
await page.evaluate(()=>{localStorage.removeItem('stethofuse-demo-v1');sessionStorage.setItem('stethofuse-demo-persona','USR-1001');});
await go('/app/dashboard');

await check('Staff A dashboard and per-account collection',async()=>{
 assert.match(await page.locator('h1').innerText(),/Amina/);
 await page.screenshot({path:path.join(evidence,'staff-dashboard-1440.png'),fullPage:true});
 await go('/app/recordings');
 assert(await page.getByText('Morning chest recording',{exact:true}).count());
 assert.equal(await page.getByText('Daniel’s baseline recording',{exact:true}).count(),0);
 await page.getByLabel('Search recordings',{exact:true}).fill('REC-1042');
 assert.equal(await page.locator('tbody tr').count(),1);
 await page.reload();await page.locator('h1').waitFor();
 assert(await page.getByText('Morning chest recording',{exact:true}).count());
});
await check('Staff B isolated across refresh and denied private deep link',async()=>{
 await persona('USR-1002','/app/recordings');
 assert(await page.getByText('Daniel’s baseline recording',{exact:true}).count());
 assert.equal(await page.getByText('Morning chest recording',{exact:true}).count(),0);
 await page.reload();await page.locator('h1').waitFor();
 assert.equal(await page.getByText('Morning chest recording',{exact:true}).count(),0);
 await go('/app/recordings/REC-1042');assert.match(await page.locator('h1').innerText(),/private/);
});
await check('Admin has no automatic private audio access',async()=>{
 await persona('USR-3001','/app/recordings/REC-1042');assert.match(await page.locator('h1').innerText(),/private/);
});

let createdId,createdJob;
await check('Reject renamed non-WAV data and accept a valid RIFF PCM file',async()=>{
 await persona('USR-1001','/app/recordings/new/upload');
 await page.getByLabel('Choose WAV recording',{exact:true}).setInputFiles({name:'not-a-wave.wav',mimeType:'audio/wav',buffer:Buffer.alloc(80,44)});
 await page.getByText(/not a RIFF\/WAVE recording/).waitFor();
 const rate=16000,samples=32000,buffer=Buffer.alloc(44+samples*2);
 buffer.write('RIFF');buffer.writeUInt32LE(buffer.length-8,4);buffer.write('WAVE',8);buffer.write('fmt ',12);buffer.writeUInt32LE(16,16);buffer.writeUInt16LE(1,20);buffer.writeUInt16LE(1,22);buffer.writeUInt32LE(rate,24);buffer.writeUInt32LE(rate*2,28);buffer.writeUInt16LE(2,32);buffer.writeUInt16LE(16,34);buffer.write('data',36);buffer.writeUInt32LE(samples*2,40);
 for(let i=0;i<samples;i++)buffer.writeInt16LE(Math.round(Math.sin(i/rate*2*Math.PI*90)*5000),44+i*2);
 await page.getByLabel('Choose WAV recording',{exact:true}).setInputFiles({name:'synthetic-review.wav',mimeType:'audio/wav',buffer});
 await page.getByText('WAV header validated locally').waitFor();
 await page.getByLabel('Recording title',{exact:true}).fill('Workflow fixture • upload');
 await page.getByLabel('Pseudonymous sample label').fill('SYNTHETIC-TEST');
 await page.getByRole('button',{name:'Save demo recording',exact:true}).click();
 await page.waitForURL(/\/app\/recordings\/REC-/);
 createdId=page.url().split('/').at(-1);
 const stored=await page.evaluate(id=>JSON.parse(localStorage.getItem('stethofuse-demo-v1')).recordings.find(r=>r.id===id),createdId);
 assert.equal(stored.ownerId,'USR-1001');assert.equal(stored.duration,2);assert.equal(stored.metadata.label,'SYNTHETIC-TEST');
 assert(!JSON.stringify(stored).includes('base64'));assert(!Object.keys(stored).some(key=>['audio','blob','buffer','dataUrl'].includes(key)));
 await page.reload();await page.getByRole('heading',{name:'Workflow fixture • upload',exact:true}).waitFor();
 await page.screenshot({path:path.join(evidence,'recording-detail-1440.png'),fullPage:true});
});
await check('Processing survives navigation and produces linked synthetic results',async()=>{
 assert(createdId);
 await page.getByRole('button',{name:'Request ensemble run'}).click();await page.waitForURL(/\/app\/processing\/JOB-/);createdJob=page.url().split('/').at(-1);
 await page.getByText('Current simulated stage').waitFor();
 await page.getByRole('link',{name:'Back to the dashboard'}).click();
 await page.locator('h1').waitFor();
 await go(`/app/processing/${createdJob}`);
 await page.getByRole('link',{name:'Open result',exact:true}).waitFor({timeout:35000});
 await page.getByRole('link',{name:'Open result',exact:true}).click();await page.waitForURL(/\/app\/results\/RES-/);
 await page.getByText('Heart component',{exact:true}).waitFor();
 await page.getByRole('tab',{name:'Spectrograms',exact:true}).click();
 assert.equal(await page.locator('canvas').count(),3);
 await page.getByRole('tab',{name:'Run provenance',exact:true}).click();
 await page.getByText('Candidate experts',{exact:true}).waitFor();
 await page.getByRole('tab',{name:'Listen & inspect',exact:true}).click();
 await page.getByRole('button',{name:'Play heart',exact:true}).click();
 await page.getByRole('button',{name:'Pause heart',exact:true}).waitFor();
 await page.getByRole('button',{name:'Pause heart',exact:true}).click();
 const downloadPromise=page.waitForEvent('download');
 await page.getByRole('button',{name:'Download synthetic heart WAV',exact:true}).click();
 const download=await downloadPromise,stream=await download.createReadStream(),chunks=[];
 for await(const chunk of stream)chunks.push(chunk);
 const wav=Buffer.concat(chunks);assert.equal(wav.toString('ascii',0,4),'RIFF');assert.equal(wav.toString('ascii',8,12),'WAVE');assert.match(download.suggestedFilename(),/^DEMO-synthetic-heart-/);
 await page.screenshot({path:path.join(evidence,'result-workspace-1440.png'),fullPage:true});
});

let assignmentId;
await check('Owner can assign an analyst, who can save and submit a timestamped review',async()=>{
 await go(`/app/recordings/${createdId}`);
 await page.getByRole('button',{name:'Share or assign',exact:true}).click();
 await page.getByLabel('Recipient',{exact:true}).selectOption('USR-2001');
 await page.getByRole('button',{name:'Grant demo access',exact:true}).click();
 await page.getByRole('dialog').waitFor({state:'hidden'});
 assignmentId=await page.evaluate(id=>JSON.parse(localStorage.getItem('stethofuse-demo-v1')).assignments.find(a=>a.recordingId===id&&a.analystId==='USR-2001').id,createdId);
 await persona('USR-2001',`/app/reviews/${assignmentId}`);
 await page.getByLabel('Time in seconds',{exact:true}).fill('0.7');
 await page.getByLabel('Observation',{exact:true}).fill('Synthetic sample contains a brief amplitude change.');
 await page.getByRole('button',{name:'Add note',exact:true}).click();
 await page.getByLabel('Review summary').fill('Fictional research review. No clinical interpretation.');
 await page.getByRole('button',{name:'Save draft',exact:true}).click();
 await page.reload();await page.locator('h1').waitFor();
 assert.equal(await page.getByLabel('Review summary').inputValue(),'Fictional research review. No clinical interpretation.');
 await page.getByText('Synthetic sample contains a brief amplitude change.',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Submit review',exact:true}).click();
 await page.getByRole('button',{name:'Submit decision',exact:true}).click();
 await page.getByRole('dialog').first().waitFor({state:'hidden'});
 await page.screenshot({path:path.join(evidence,'analyst-review-1440.png'),fullPage:true});
 await go('/app/review-history');assert(await page.getByText('Workflow fixture • upload',{exact:true}).count());
});
await check('Revocation immediately denies analyst recording, result and review deep links',async()=>{
 await persona('USR-1001',`/app/recordings/${createdId}`);
 await page.getByRole('button',{name:'Revoke',exact:true}).click();
 await page.getByRole('button',{name:'Revoke access',exact:true}).click();
 await persona('USR-2001',`/app/recordings/${createdId}`);assert.match(await page.locator('h1').innerText(),/private/);
 await go(`/app/reviews/${assignmentId}`);assert.match(await page.locator('h1').innerText(),/private/);
 const resultId=await page.evaluate(id=>JSON.parse(localStorage.getItem('stethofuse-demo-v1')).results.find(r=>r.recordingId===id).id,createdId);
 await go(`/app/results/${resultId}`);assert.match(await page.locator('h1').innerText(),/private/);
 await page.screenshot({path:path.join(evidence,'revoked-access.png'),fullPage:true});
});
await check('Capture simulator error states and start/stop/save workflow',async()=>{
 await persona('USR-1002','/app/recordings/new/record');
 for(const [scenario,message] of [['denied','Permission denied · simulated'],['no-device','No input device · simulated'],['unsupported','Capture unsupported · simulated']]){
  await page.getByLabel('Preview capture state').selectOption(scenario);
  await page.getByRole('button',{name:'Connect demo input'}).click();await page.getByText(message,{exact:true}).waitFor();
 }
 await page.getByLabel('Preview capture state').selectOption('normal');
 await page.getByRole('button',{name:'Connect demo input'}).click();
 await page.getByRole('button',{name:'Start demo capture'}).click();
 await page.getByRole('button',{name:'Stop capture'}).waitFor();await page.waitForTimeout(1300);
 await page.getByRole('button',{name:'Stop capture'}).click();
 await page.getByLabel('Recording title',{exact:true}).fill('Daniel synthetic capture');
 await page.getByRole('button',{name:'Save demo recording',exact:true}).click();await page.waitForURL(/\/app\/recordings\/REC-/);
 await page.getByRole('heading',{level:1,name:'Daniel synthetic capture',exact:true}).waitFor();
});
await check('Failed run remains failed and retry creates another historical run',async()=>{
 await persona('USR-1001','/app/processing/JOB-2102');
 await page.getByText('Processing interrupted',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Retry as a new run'}).click();await page.waitForURL(url=>!url.pathname.endsWith('JOB-2102'));
 const statuses=await page.evaluate(()=>JSON.parse(localStorage.getItem('stethofuse-demo-v1')).jobs.filter(j=>j.recordingId==='REC-1044').map(j=>j.status));
 assert(statuses.includes('failed'));assert(statuses.includes('queued')||statuses.includes('processing'));
});
await check('Metadata editing guards unsaved navigation and saves to own account',async()=>{
 await go(`/app/recordings/${createdId}`);await page.getByRole('button',{name:'Edit',exact:true}).click();
 await page.getByLabel('Recording title',{exact:true}).fill('Reviewed synthetic upload');
 await page.getByRole('link',{name:'My recordings',exact:true}).click();
 await page.getByRole('dialog',{name:'Leave unsaved changes?'}).waitFor();
 await page.getByRole('button',{name:'Stay here',exact:true}).click();
 await page.getByRole('button',{name:'Save context',exact:true}).click();
 await page.getByRole('heading',{name:'Reviewed synthetic upload',exact:true}).waitFor();
 await page.reload();await page.getByRole('heading',{name:'Reviewed synthetic upload',exact:true}).waitFor();
});
await check('Archive, restore and rename mutate only owned metadata',async()=>{
 await go('/app/recordings');await page.getByLabel('Search recordings',{exact:true}).fill(createdId);
 await page.getByRole('button',{name:'Archive',exact:true}).click();await page.getByText('No matching recordings',{exact:true}).waitFor();
 await page.getByRole('tab',{name:/Archived/}).click();await page.getByRole('button',{name:'Restore',exact:true}).click();
 await page.getByRole('tab',{name:/Collection/}).click();await page.getByRole('button',{name:'Rename',exact:true}).click();
 await page.getByRole('dialog').getByLabel('Recording title',{exact:true}).fill('Renamed synthetic upload');
 await page.getByRole('button',{name:'Save name',exact:true}).click();await page.locator('tbody').getByText('Renamed synthetic upload',{exact:true}).waitFor();
});
await check('Cancellation leaves the original intact and historical run visible',async()=>{
 await go(`/app/recordings/${createdId}`);await page.getByRole('button',{name:'Request ensemble run'}).click();
 await page.getByRole('button',{name:'Cancel demo run',exact:true}).click();
 await page.getByRole('button',{name:'Cancel run',exact:true}).click();await page.getByRole('heading',{name:'This run was cancelled.',exact:true}).waitFor();
 await page.getByRole('link',{name:'View recording',exact:true}).click();await page.getByRole('heading',{name:'Renamed synthetic upload',exact:true}).waitFor();
});
await check('Analyst can request re-recording with a non-diagnostic summary',async()=>{
 await persona('USR-2001','/app/reviews/ASN-402');
 await page.getByLabel('Review summary').fill('Synthetic contact noise obscures part of this sample; capture another research sample.');
 await page.getByLabel('Decision',{exact:true}).selectOption('re-record');
 await page.getByRole('button',{name:'Submit review',exact:true}).click();await page.getByRole('button',{name:'Submit decision',exact:true}).click();
 await go('/app/review-history');await page.getByText('re record',{exact:true}).waitFor();
});
await check('Mobile workspace is contained and key routes refresh',async()=>{
 await persona('USR-1001');
 await page.setViewportSize({width:390,height:844});
 const resultId=await page.evaluate(id=>JSON.parse(localStorage.getItem('stethofuse-demo-v1')).results.find(r=>r.recordingId===id).id,createdId);
 for(const route of ['/app/dashboard','/app/recordings','/app/recordings/new','/app/recordings/new/upload','/app/recordings/new/record',`/app/recordings/${createdId}`,`/app/results/${resultId}`,`/app/processing/${createdJob}`,'/app/shared','/app/results','/app/history']){
  await go(route);assert(await page.locator('h1').count());
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),`Overflow at ${route}`);
 }
 await go('/app/dashboard');await page.screenshot({path:path.join(evidence,'staff-dashboard-390.png'),fullPage:true});
 await go('/app/recordings');await page.screenshot({path:path.join(evidence,'recordings-390.png'),fullPage:true});
});
await check('Delete confirmation removes only the selected demo recording and runs',async()=>{
 await page.setViewportSize({width:1440,height:1000});await go('/app/recordings');
 await page.getByLabel('Search recordings',{exact:true}).fill(createdId);
 await page.getByRole('button',{name:'Delete Renamed synthetic upload',exact:true}).click();
 await page.getByRole('button',{name:'Delete recording',exact:true}).click();
 await page.getByText('No matching recordings',{exact:true}).waitFor();
 const intact=await page.evaluate(id=>{const s=JSON.parse(localStorage.getItem('stethofuse-demo-v1'));return !s.recordings.some(r=>r.id===id)&&!s.jobs.some(j=>j.recordingId===id)&&s.recordings.some(r=>r.id==='REC-1047');},createdId);assert(intact);
});
await check('No JavaScript runtime errors in workflow run',async()=>assert.deepEqual(errors,[]));
await writeFile(path.join(evidence,'results.json'),JSON.stringify({browser:'Google Chrome, headless Linux',viewport:'1440×1000 and 390×844',passes,failures,errors,testedAt:new Date().toISOString()},null,2));
await browser.close();
console.log(JSON.stringify({passes:passes.length,failures},null,2));
if(failures.length)process.exitCode=1;

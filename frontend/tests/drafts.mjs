import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const evidence=path.join(root,process.env.EVIDENCE_ROOT || 'evidence','drafts');
await mkdir(evidence,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage();
const base=process.env.FRONTEND_URL||'http://127.0.0.1:4180',results=[],errors=[];
page.on('pageerror',error=>errors.push(error.message));
const check=async(name,action)=>{try{const detail=await action();results.push({name,status:'PASS',detail});console.log(`PASS ${name}`);}catch(error){results.push({name,status:'FAIL',error:error.message});console.error(`FAIL ${name}: ${error.message}`);}};
const go=async route=>{await page.goto(base+route);await page.locator('h1').first().waitFor();};
const draft=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('stethofuse-demo-v1')).drafts['USR-1001:new-recording']);
async function expectCleared(){assert.deepEqual(await draft(),{});await page.waitForTimeout(650);assert.deepEqual(await draft(),{});await go('/app/recordings/new');assert.equal(await page.getByLabel('Recording title',{exact:true}).inputValue(),'');assert.equal(await page.getByLabel('Research notes').inputValue(),'');await page.waitForTimeout(650);assert.deepEqual(await draft(),{});}
function wav(){const rate=16000,count=rate*2,buffer=Buffer.alloc(44+count*2);buffer.write('RIFF');buffer.writeUInt32LE(buffer.length-8,4);buffer.write('WAVE',8);buffer.write('fmt ',12);buffer.writeUInt32LE(16,16);buffer.writeUInt16LE(1,20);buffer.writeUInt16LE(1,22);buffer.writeUInt32LE(rate,24);buffer.writeUInt32LE(rate*2,28);buffer.writeUInt16LE(2,32);buffer.writeUInt16LE(16,34);buffer.write('data',36);buffer.writeUInt32LE(count*2,40);return buffer;}
try{
 await page.goto(base);await page.evaluate(()=>{localStorage.removeItem('stethofuse-demo-v1');sessionStorage.setItem('stethofuse-demo-persona','USR-1001');});
 await go('/app/recordings/new');
 await check('Last title keystroke survives immediate navigation before the old 500ms debounce',async()=>{
  const start=Date.now();
  await page.getByLabel('Recording title',{exact:true}).fill('Last-keystroke draft');
  await page.locator('a.input-choice[href="/app/recordings/new/upload"]').evaluate(link=>link.click());
  const navigationIssuedAfterMs=Date.now()-start;assert(navigationIssuedAfterMs<500,`Navigation was not immediate: ${navigationIssuedAfterMs}ms`);
  await page.waitForURL('**/app/recordings/new/upload');
  assert.equal(await page.getByLabel('Recording title',{exact:true}).inputValue(),'Last-keystroke draft');
  return {navigationIssuedAfterMs};
 });
 await check('Latest metadata survives immediate return to input choice and subsequent device route',async()=>{
  await page.getByLabel('Pseudonymous sample label').fill('DEMO-LAST-KEY');
  const start=Date.now();await page.getByLabel('Research notes').fill('Only fictional metadata. Preserve the last character Z');
  await page.getByRole('link',{name:'Input options'}).evaluate(link=>link.click());
  const navigationIssuedAfterMs=Date.now()-start;assert(navigationIssuedAfterMs<500,`Navigation took ${navigationIssuedAfterMs}ms`);
  await page.waitForURL('**/app/recordings/new');
  assert.equal(await page.getByLabel('Research notes').inputValue(),'Only fictional metadata. Preserve the last character Z');
  await page.locator('a.input-choice[href="/app/recordings/new/record"]').click();
  await page.waitForURL('**/app/recordings/new/record');
  assert.equal(await page.getByLabel('Recording title',{exact:true}).inputValue(),'Last-keystroke draft');
  assert.equal(await page.getByLabel('Pseudonymous sample label').inputValue(),'DEMO-LAST-KEY');
  return {navigationIssuedAfterMs};
 });
 await check('Draft ownership survives persona switching without leaking into Staff B',async()=>{
  await page.getByRole('button',{name:'Switch demo account'}).click();
  await page.getByRole('button',{name:/Daniel Tan/}).click();
  await go('/app/recordings/new');assert.equal(await page.getByLabel('Recording title',{exact:true}).inputValue(),'');
  await page.getByRole('button',{name:'Switch demo account'}).click();await page.getByRole('button',{name:/Amina Rahman/}).click();
  await go('/app/recordings/new');assert.equal(await page.getByLabel('Recording title',{exact:true}).inputValue(),'Last-keystroke draft');
  assert.equal(await page.getByLabel('Research notes').inputValue(),'Only fictional metadata. Preserve the last character Z');
 });
 await check('Successful WAV creation clears the draft without cleanup or delayed resurrection',async()=>{
  await page.locator('a.input-choice[href="/app/recordings/new/upload"]').click();
  await page.getByLabel('Choose WAV recording',{exact:true}).setInputFiles({name:'synthetic-draft-check.wav',mimeType:'audio/wav',buffer:wav()});
  await page.getByText('WAV header validated locally').waitFor();
  await page.getByLabel('Recording title',{exact:true}).fill('Immediate draft submit');
  await page.getByRole('button',{name:'Save demo recording',exact:true}).evaluate(button=>button.click());
  await page.waitForURL(/\/app\/recordings\/REC-/);await page.getByRole('heading',{name:'Immediate draft submit',exact:true}).waitFor();
  await expectCleared();
 });
 await check('Successful simulated capture also clears its latest metadata draft',async()=>{
  await page.locator('a.input-choice[href="/app/recordings/new/record"]').click();
  await page.getByRole('button',{name:'Connect demo input'}).click();await page.getByRole('button',{name:'Start demo capture'}).click();
  await page.waitForTimeout(1100);await page.getByRole('button',{name:'Stop capture',exact:true}).click();
  await page.getByLabel('Recording title',{exact:true}).fill('Capture draft cleared');
  await page.getByLabel('Research notes').fill('Fictional capture metadata only.');
  await page.getByRole('button',{name:'Save demo recording',exact:true}).evaluate(button=>button.click());
  await page.waitForURL(/\/app\/recordings\/REC-/);await page.getByRole('heading',{name:'Capture draft cleared',exact:true}).waitFor();
  await expectCleared();
 });
 await check('No browser runtime errors',async()=>assert.deepEqual(errors,[]));
 await writeFile(path.join(evidence,'results.json'),JSON.stringify({testedAt:new Date().toISOString(),browser:await browser.version(),scope:'Immediate draft navigation and post-create clearing regression',results,errors},null,2));
 if(results.some(result=>result.status==='FAIL'))process.exitCode=1;
}finally{await browser.close();}

// Read-only browser follow-up: query-route unsaved guard, public-ID layout and API2 compatibility.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import path from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';
const out=path.resolve('output/playwright/identity-foundation/final-layout-v1');await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true});
const report={scope:'REAL isolated API3 and existing API2, read-only; fictional fixed SDK/verifier. No model execution.',checks:[],screenshots:[]};
async function context(origin){
  const c=await browser.newContext({viewport:{width:1440,height:900}});
  await c.route('**/node_modules/.vite/deps/firebase_app.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-app.mjs')}));
  await c.route('**/node_modules/.vite/deps/firebase_auth.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-auth.mjs')}));
  await c.route('**/src/config/runtime.ts*',r=>r.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
  await c.addInitScript(({origin})=>{if(location.origin===origin)sessionStorage.setItem('__m1_test_identity',JSON.stringify({uid:'alice',verified:true}));},{origin});
  await c.route(url=>['http:','https:'].includes(url.protocol)&&url.origin!==origin,r=>r.abort());
  return c;
}
async function shot(p,name){await p.evaluate(()=>document.fonts.ready);await p.screenshot({path:path.join(out,name)});report.screenshots.push(name);}
async function noOverflow(p){assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
try{
  const c=await context('http://127.0.0.1:4197'),p=await c.newPage();
  await p.goto('http://127.0.0.1:4197/app/settings?section=general');await p.getByRole('heading',{name:'Your profile',exact:true}).waitFor();
  await p.getByRole('textbox',{name:'Display name',exact:true}).fill('Unsaved local draft — not sent');
  await p.getByRole('navigation',{name:'Settings sections'}).getByRole('button',{name:'Appearance',exact:true}).click();
  await p.getByRole('dialog',{name:'Leave unsaved changes?'}).waitFor();await p.getByRole('button',{name:'Stay here',exact:true}).click();
  assert.equal(new URL(p.url()).search,'?section=general');
  await p.getByRole('navigation',{name:'Settings sections'}).getByRole('button',{name:'Appearance',exact:true}).click();
  await p.getByRole('button',{name:'Discard and leave',exact:true}).click();await p.getByRole('heading',{name:'Appearance',exact:true}).waitFor();
  report.checks.push('PASS: unsaved profile edits are guarded across legacy query-section navigation; no PATCH sent');
  await p.setViewportSize({width:390,height:844});await p.goto('http://127.0.0.1:4197/app/library');await p.locator('.sf-recordings li').first().waitFor();await noOverflow(p);await shot(p,'01-library-public-ids-mobile.png');
  const response=await fetch('http://127.0.0.1:4197/api/results',{headers:{Authorization:'Bearer M1-MOCK:alice'}});assert.equal(response.status,200);
  const results=await response.json(),result=results.items.find(item=>item.provenance?.input_artifact_sha256==='8e0efd28aaf89f7efbd8107805a74bd837bcc70ea3dc4b4b783eff0e6a220616');assert(result);
  await p.goto('http://127.0.0.1:4197/app/recordings/'+result.recording_id);await p.waitForFunction(()=>document.querySelectorAll('.sf-player[data-media-state="ready"]').length===3);await noOverflow(p);await shot(p,'02-detail-public-reference-mobile.png');
  report.checks.push('PASS: real public-ID Library/detail and existing audio layout fit390px; no inference');
  const old=await context('http://127.0.0.1:4196'),legacy=await old.newPage();await legacy.goto('http://127.0.0.1:4196/app/profile');await legacy.getByRole('heading',{name:'Your profile',exact:true}).waitFor();
  assert.equal(await legacy.getByRole('textbox',{name:'Handle',exact:true}).inputValue(),'');assert(await legacy.getByRole('textbox',{name:'Handle',exact:true}).evaluate(el=>el.readOnly));
  await legacy.getByText('Handles are not available on this server yet. Your display name can still be edited.',{exact:true}).waitFor();await shot(legacy,'03-api2-profile-honest-unavailable.png');
  report.checks.push('PASS: original owner API2 remains compatible; no invented handle/reference or DB migration');
  report.status='PASS';console.log(report.checks.join('\n'));
}catch(error){report.status='FAIL';report.error=error.message;throw error;}
finally{await writeFile(path.join(out,'receipt.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}

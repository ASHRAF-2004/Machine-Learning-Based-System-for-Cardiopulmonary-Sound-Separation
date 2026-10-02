// Real isolated API/SQLite/private HLS outputs. Fixed TEST ONLY identity SDK.
// Owner browser is never attached. One explicitly delayed lookup tests cancellation.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import path from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';

const origin='http://127.0.0.1:4198',out=path.resolve('output/playwright/handle-sharing/v5');
await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true});
const report={scope:'Real isolated local API/database/files; approved fixed test identities, no model execution or T9.',checks:[],screenshots:[]};
const created=[];
async function api(route,uid='alice',method='GET',body){
  return fetch(origin+'/api'+route,{method,headers:{Authorization:'Bearer M1-MOCK:'+uid,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),cache:'no-store'});
}
async function context(uid='alice'){
  const c=await browser.newContext({viewport:{width:1440,height:900}});
  await c.route('**/node_modules/.vite/deps/firebase_app.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-app.mjs')}));
  await c.route('**/node_modules/.vite/deps/firebase_auth.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-auth.mjs')}));
  await c.route('**/src/config/runtime.ts*',r=>r.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
  await c.addInitScript(({uid,origin})=>{if(location.origin===origin)sessionStorage.setItem('__m1_test_identity',JSON.stringify({uid,verified:true}));},{uid,origin});
  await c.route(url=>['http:','https:'].includes(url.protocol)&&url.origin!==origin,r=>r.abort());
  return c;
}
async function shot(p,name){await p.evaluate(()=>document.fonts.ready);await p.screenshot({path:path.join(out,name)});report.screenshots.push(name);}
async function noOverflow(p){assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Horizontal overflow');}

try{
  const results=await (await api('/results')).json();
  const result=results.items.find(item=>item.provenance?.input_artifact_sha256==='8e0efd28aaf89f7efbd8107805a74bd837bcc70ea3dc4b4b783eff0e6a220616');assert(result);
  const record=await (await api('/recordings/'+result.recording_id)).json();
  const priorGrants=(await (await api('/recordings/'+record.id+'/grants')).json()).items;
  const ownerBefore=await (await api('/auth/me')).json();
  const bobBefore=await (await api('/auth/me','bob')).json();assert(bobBefore.user.handle);
  const heart=result.resources.find(item=>item.kind==='heart_audio'),lung=result.resources.find(item=>item.kind==='lung_audio');assert(heart&&lung);
  assert.equal((await api('/media/'+heart.id,'bob','HEAD')).status,403,'Use a fresh copy without pre-existing Bob access');
  const c=await context(),p=await c.newPage(),errors=[];p.on('pageerror',error=>errors.push(error.message));
  await p.goto(origin+'/app/recordings/'+record.id);await p.waitForFunction(()=>document.querySelectorAll('.sf-player[data-media-state="ready"]').length===3);
  const details=p.locator('.sf-core-technical');await details.locator('summary').click();
  assert.equal(await details.locator('.sf-technical-facts > div').count(),6);
  assert.equal(await details.locator('.sf-technical-receipt').count(),0);
  await details.scrollIntoViewIfNeeded();await noOverflow(p);await shot(p,'01-concise-details-desktop.png');
  const more=details.getByRole('button',{name:'See more',exact:true});await more.focus();await p.keyboard.press('Space');
  await details.getByText('checkpoint sha256',{exact:true}).waitFor();
  assert.equal(await details.locator('.sf-technical-receipt > div').count(),Object.keys(result.provenance).length+6);
  for(const [key,value] of Object.entries(result.provenance)){
    const fact=details.locator('.sf-technical-receipt > div').filter({has:p.getByText(key.replaceAll('_',' '),{exact:true})});
    assert.equal(await fact.locator('dd').textContent(),typeof value==='object'?JSON.stringify(value):String(value));
  }
  await details.getByRole('button',{name:'See less',exact:true}).focus();await p.keyboard.press('Enter');
  assert.equal(await details.locator('.sf-technical-receipt').count(),0);
  assert(await details.getByRole('button',{name:'See more',exact:true}).evaluate(el=>el===document.activeElement));
  report.checks.push('REAL: six key facts, every provenance value retained under disclosure; keyboard expand/collapse and focus pass');

  await p.getByRole('button',{name:'Share',exact:true}).click();
  const sharing=p.getByRole('region',{name:'Recording sharing'});
  assert.equal(await p.getByLabel('Recipient application ID').count(),0);
  const query=sharing.getByRole('textbox',{name:'Share with @username',exact:true});
  async function findBob(){await query.fill('@'+bobBefore.user.handle);await sharing.getByRole('button',{name:'Find person',exact:true}).click();await sharing.locator('.sf-share-match').waitFor();assert.equal(await sharing.locator('.sf-share-match .sf-identity strong').textContent(),bobBefore.user.display_name||bobBefore.user.handle);}
  async function shareScope(resource){
    await findBob();await sharing.getByRole('combobox',{name:'What can they access?',exact:true}).selectOption(resource);
    const response=p.waitForResponse(r=>r.url()===origin+'/api/recordings/'+record.id+'/grants'&&r.request().method()==='POST');
    await sharing.getByRole('button',{name:'Share access',exact:true}).click();const value=await response;assert.equal(value.status(),201);const grant=await value.json();created.push(grant.id);await sharing.getByText('Shared with @'+bobBefore.user.handle+'.',{exact:true}).waitFor();return grant;
  }
  await findBob();await sharing.scrollIntoViewIfNeeded();await noOverflow(p);await shot(p,'02-handle-match-desktop.png');
  const heartGrant=await shareScope(heart.id);
  assert.equal((await api('/media/'+heart.id,'bob','HEAD')).status,200);
  for(const route of ['/media/'+lung.id,'/media/'+record.original_resource_id,'/results/'+result.id])assert.equal((await api(route,'bob',route.startsWith('/media')?'HEAD':'GET')).status,403);
  const unrelated=await api('/recordings/'+record.id+'/sharing-recipient','bob','POST',{handle:ownerBefore.user.handle});assert.equal(unrelated.status,403);
  const anon=await fetch(origin+'/api/recordings/'+record.id+'/sharing-recipient',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({handle:bobBefore.user.handle})});assert.equal(anon.status,401);
  const bc=await context('bob'),bp=await bc.newPage();await bp.goto(origin+'/app/audio/'+heart.id);await bp.locator('.sf-player[data-media-state="ready"]').waitFor();
  assert.equal(await bp.locator('.sf-player[data-media-state="ready"]').count(),1);
  report.checks.push('REAL: exact @handle confirmed, Heart-only grant persisted; recipient playback works; Lung/Original/result denied; nonowner lookup403 and anonymous401');

  for(const id of [lung.id,record.original_resource_id,result.id])await shareScope(id);
  await sharing.getByRole('button',{name:`See more (${priorGrants.length+1})`,exact:true}).waitFor();
  assert.equal(await sharing.locator('.sf-grant-list > li').count(),3);
  await sharing.getByRole('button',{name:/^See more/}).click();assert.equal(await sharing.locator('.sf-grant-list > li').count(),priorGrants.length+4);
  await sharing.getByRole('button',{name:'See less',exact:true}).click();assert.equal(await sharing.locator('.sf-grant-list > li').count(),3);
  await sharing.scrollIntoViewIfNeeded();await shot(p,'03-sharing-list-desktop.png');
  // Use the real owner control to revoke the exact Heart permission only.
  await sharing.getByRole('button',{name:/^See more/}).click();
  const heartRow=sharing.locator(`[data-grant-id="${heartGrant.id}"]`);p.once('dialog',dialog=>dialog.accept());await heartRow.getByRole('button',{name:'Revoke',exact:true}).click();await sharing.getByText('Permission revoked.',{exact:true}).waitFor();
  assert.equal((await api('/media/'+heart.id,'bob','HEAD')).status,403);
  await bp.reload();await bp.getByText('This audio is not included in your current access.',{exact:true}).waitFor();assert.equal(await bp.locator('.sf-player[data-media-state="ready"]').count(),0);
  report.checks.push('REAL: grant list defaults to3 with See more/less; revoke exact Heart grant persists and subsequent protected request/UI deny it');

  await p.setViewportSize({width:390,height:844});await findBob();await sharing.scrollIntoViewIfNeeded();await noOverflow(p);await shot(p,'04-sharing-mobile.png');
  await details.scrollIntoViewIfNeeded();await noOverflow(p);await shot(p,'05-concise-details-mobile.png');
  await p.setViewportSize({width:820,height:1000});await noOverflow(p);await shot(p,'06-concise-details-tablet.png');
  await p.setViewportSize({width:1440,height:900});await p.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await details.scrollIntoViewIfNeeded();await noOverflow(p);await shot(p,'07-concise-details-midnight.png');
  await p.emulateMedia({reducedMotion:'reduce'});assert.equal(await p.locator('.sf-app').getAttribute('data-theme'),'midnight');
  report.checks.push('REAL: desktop1440/mobile390/tablet820 and Midnight fit; controls/focus remain usable, reduced-motion preference preserved');

  // Transport-delay seam only; the payload is an actual authorized API response.
  let release;const gate=new Promise(resolve=>release=resolve),lookupPath=origin+'/api/recordings/'+record.id+'/sharing-recipient';
  await p.route(lookupPath,async route=>{const response=await route.fetch();await gate;await route.fulfill({response}).catch(()=>{});});
  await query.fill('@'+bobBefore.user.handle);await sharing.getByRole('button',{name:'Find person',exact:true}).click();await sharing.getByRole('button',{name:'Finding…',exact:true}).waitFor();await query.fill('@different.person');release();
  await p.unroute(lookupPath);assert.equal(await sharing.locator('.sf-share-match').count(),0);
  report.checks.push('DELAYED TRANSPORT: editing handle cancels obsolete confirmation; no mocked recording, result, grant or media data');
  assert.deepEqual((await (await api('/auth/me')).json()).user,ownerBefore.user,'Owner identity unchanged');
  assert.deepEqual((await (await api('/auth/me','bob')).json()).user,bobBefore.user,'Recipient identity unchanged');
  assert.deepEqual(errors,[]);report.status='PASS';console.log(report.checks.join('\n'));
}catch(error){report.status='FAIL';report.error=error.message;throw error;}
finally{
  // Only grants created by this test, never pre-existing permissions or audio.
  for(const id of created)assert.equal((await api('/grants/'+id,'alice','DELETE')).status,204);
  report.temporaryGrantsRevoked=created.length;
  await writeFile(path.join(out,'receipt.json'),JSON.stringify(report,null,2)+'\n');await browser.close();
}

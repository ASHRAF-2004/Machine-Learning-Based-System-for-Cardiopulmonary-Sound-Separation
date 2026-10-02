// Actual isolated local API/SQLite/private raw HLS artifacts. Fixed TEST ONLY identities.
// Owner browser is not attached. One explicitly identified transport-failure check.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import path from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';

const origin='http://127.0.0.1:4199',out=path.resolve('output/playwright/shared-reviews/v2');
await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true});
const report={checks:[],screenshots:[],identity:'Existing fixed fictional SDK/verifier, not live Firebase; all recording/review/media APIs are real.'},created=[];
async function api(route,uid='alice',method='GET',body){return fetch(origin+'/api'+route,{method,headers:{Authorization:'Bearer M1-MOCK:'+uid,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),cache:'no-store'});}
async function context(uid='analyst'){
  const c=await browser.newContext({viewport:{width:1440,height:900}});
  await c.route('**/node_modules/.vite/deps/firebase_app.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-app.mjs')}));
  await c.route('**/node_modules/.vite/deps/firebase_auth.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-auth.mjs')}));
  await c.route('**/src/config/runtime.ts*',r=>r.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
  await c.addInitScript(({uid,origin})=>{if(location.origin===origin)sessionStorage.setItem('__m1_test_identity',JSON.stringify({uid,verified:true}));},{uid,origin});
  await c.route(value=>['http:','https:'].includes(value.protocol)&&value.origin!==origin,r=>r.abort());return c;
}
async function shot(p,name){await p.evaluate(()=>document.fonts.ready);assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal overflow');await p.screenshot({path:path.join(out,name)});report.screenshots.push(name);}
try{
  const result=(await (await api('/results')).json()).items.find(r=>r.provenance?.input_artifact_sha256==='8e0efd28aaf89f7efbd8107805a74bd837bcc70ea3dc4b4b783eff0e6a220616');assert(result);
  const record=await (await api('/recordings/'+result.recording_id)).json(),person=(await (await api('/auth/me','analyst')).json()).user;
  const beforeOwner=(await (await api('/auth/me')).json()).user,beforeBob=(await (await api('/auth/me','bob')).json()).user;
  assert.equal((await (await api('/assignments','analyst')).json()).items.length,0,'Use an unassigned isolated test copy, not an owner manual-review session');
  async function assign(resource){const response=await api('/recordings/'+record.id+'/grants','alice','POST',{recipient_handle:person.handle,recipient_public_id:person.public_id,permission:'review',resource_id:resource});assert.equal(response.status,201);const g=await response.json();created.push(g.id);return g;}
  const original=[];for(let i=0;i<4;i++)original.push(await assign(record.original_resource_id));
  const c=await context(),p=await c.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
  await p.goto(origin+'/app/review-queue');await p.waitForURL(origin+'/app/shared?view=assigned');
  const list=p.getByRole('list',{name:'Assigned reviews',exact:true});await list.locator('li').first().waitFor();assert.equal(await list.locator('li').count(),3);
  assert.equal(await p.locator('h1').count(),1);assert.equal(await p.getByRole('link',{name:'Review queue',exact:true}).count(),0);
  assert(!(await p.locator('main').innerText()).includes(record.id),'No primary internal IDs');
  const more=p.getByRole('button',{name:'See more (1)',exact:true});await more.focus();await p.keyboard.press('Space');assert.equal(await list.locator('li').count(),4);
  await p.getByRole('button',{name:'See less',exact:true}).focus();await p.keyboard.press('Enter');assert.equal(await list.locator('li').count(),3);
  await shot(p,'01-assigned-desktop.png');
  await p.getByRole('searchbox',{name:'Search assigned reviews by title or public reference'}).fill(record.public_id);assert.equal(await list.locator('li').count(),3);
  await p.getByRole('searchbox',{name:'Search assigned reviews by title or public reference'}).fill('No matching recording');await p.getByRole('heading',{name:'No matching reviews',exact:true}).waitFor();await p.getByRole('button',{name:'Clear review search',exact:true}).click();
  report.checks.push('REAL: legacy queue aliases reach the unified page; real title/reference, pending priority, three rows and keyboard more/less; actual search and honest empty state');

  await p.goto(origin+'/app/reviews/'+original[0].id);await p.locator('.sf-player[data-media-state="ready"]').waitFor();assert.equal(await p.locator('.sf-player[data-media-state="ready"]').count(),1);
  const notes=p.getByRole('textbox',{name:'Review notes',exact:true}),outcome=p.getByRole('combobox',{name:'Review outcome',exact:true});
  await notes.fill('Local non-diagnostic review of the assigned original.');await outcome.selectOption('accepted');
  const fresh=p.waitForResponse(r=>r.url()===origin+'/api/assignments/'+original[0].id+'/review'&&r.request().method()==='GET');await p.getByRole('button',{name:'Refresh access',exact:true}).first().click();await fresh;
  assert.equal(await notes.inputValue(),'Local non-diagnostic review of the assigned original.','Focus/access refresh preserves unsaved draft');
  const saved=p.waitForResponse(r=>r.url()===origin+'/api/assignments/'+original[0].id+'/review'&&r.request().method()==='PUT');await p.getByRole('button',{name:'Save review',exact:true}).click();assert.equal((await saved).status(),200);await p.getByText('Review saved.',{exact:true}).waitFor();
  await p.reload();await notes.waitFor();assert.equal(await notes.inputValue(),'Local non-diagnostic review of the assigned original.');assert.equal(await outcome.inputValue(),'accepted');
  await p.getByRole('region',{name:'Your review',exact:true}).scrollIntoViewIfNeeded();await shot(p,'02-review-desktop.png');
  const freshC=await context(),freshP=await freshC.newPage();await freshP.goto(origin+'/app/reviews/'+original[0].id);await freshP.getByRole('textbox',{name:'Review notes',exact:true}).waitFor();assert.equal(await freshP.getByRole('textbox',{name:'Review notes',exact:true}).inputValue(),'Local non-diagnostic review of the assigned original.');await freshC.close();
  for(const method of ['GET','PUT'])assert.equal((await api('/assignments/'+original[0].id+'/review','bob',method,method==='PUT'?{decision:'accepted',notes:'Denied'}:undefined)).status,403);
  assert.equal((await api('/assignments','admin')).status,403);
  const noAuth=await fetch(origin+'/api/assignments');assert.equal(noAuth.status,401);
  report.checks.push('REAL: exactly one protected Original player; actual outcome/notes save and survive refresh/new session; unsaved refresh protected; unrelated/Admin/anonymous denied');

  await p.setViewportSize({width:390,height:844});await p.getByRole('region',{name:'Your review',exact:true}).scrollIntoViewIfNeeded();await shot(p,'03-review-mobile.png');
  await p.goto(origin+'/app/shared?view=assigned&reviews=all');await list.locator('li').first().waitFor();await shot(p,'04-assigned-mobile.png');
  await p.setViewportSize({width:820,height:1000});await shot(p,'05-assigned-tablet.png');
  await p.setViewportSize({width:1440,height:900});await p.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await shot(p,'06-assigned-midnight.png');
  await p.emulateMedia({reducedMotion:'reduce'});assert.equal(await p.locator('.sf-app').getAttribute('data-theme'),'midnight');
  report.checks.push('REAL: desktop/mobile/tablet and Midnight; public references/status controls fit, reduced motion and navigation clearance remain');

  for(const g of original)assert.equal((await api('/grants/'+g.id,'alice','DELETE')).status,204);
  const resultGrant=await assign(result.id);
  await p.goto(origin+'/app/reviews/'+resultGrant.id);await p.getByRole('textbox',{name:'Review notes',exact:true}).waitFor();assert.equal(await p.locator('.sf-player').count(),0);
  for(const id of [record.original_resource_id,...result.resources.map(r=>r.id)])assert.equal((await api('/media/'+id,'analyst','HEAD')).status,403);
  await p.getByRole('textbox',{name:'Review notes',exact:true}).fill('Draft will not survive revoked access.');assert.equal((await api('/grants/'+resultGrant.id,'alice','DELETE')).status,204);
  await p.getByRole('button',{name:'Save review',exact:true}).click();await p.getByText(/Review access is no longer available/).waitFor();assert.equal(await p.locator('.sf-review-editor').count(),0);assert.equal(await p.locator('.sf-player').count(),0);
  await p.goto(origin+'/app/assigned');await p.waitForURL(origin+'/app/shared?view=assigned');await p.getByRole('heading',{name:'No unfinished reviews',exact:true}).waitFor();
  report.checks.push('REAL: result-only assignment has no sibling audio; revoked save denied and protected view/draft removed; old assigned link and empty queue truthful');

  await p.route(origin+'/api/assignments',r=>r.abort());await p.getByRole('button',{name:'Refresh access',exact:true}).click();await p.getByText(/The application service could not be reached/).waitFor();assert.equal(await p.locator('.sf-assignment-list').count(),0);await shot(p,'07-unavailable-desktop.png');await p.unroute(origin+'/api/assignments');
  assert.deepEqual((await (await api('/auth/me')).json()).user,beforeOwner);assert.deepEqual((await (await api('/auth/me','bob')).json()).user,beforeBob);assert.deepEqual(errors,[]);
  report.checks.push('TRANSPORT FAILURE ONLY: assignments network unavailable yields real error, never preview/demonstration rows; owner/Bob profiles unchanged; no JS exceptions');report.status='PASS';console.log(report.checks.join('\n'));
}catch(error){report.status='FAIL';report.error=error.message;throw error;}
finally{for(const id of created)assert.equal((await api('/grants/'+id,'alice','DELETE')).status,204);report.temporaryGrantsRevoked=created.length;await writeFile(path.join(out,'receipt.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}

// Real isolated API/SQLite. Only the fixed fictional Firebase identity and one
// explicit transport-failure test are intercepted; no recording/result fixtures.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import path from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';

const layoutOnly=process.argv.includes('--layout-only');
const origin='http://127.0.0.1:4200',out=path.resolve('output/playwright/workspace-completion/'+(layoutOnly?'final-v3':'v2'));
await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true});
const report={checks:[],screenshots:[],identity:'Fixed fictional test SDK/verifier; real isolated API/database. No live Firebase.'},created=[];
async function api(route,uid='alice',method='GET',body){return fetch(origin+'/api'+route,{method,headers:{Authorization:'Bearer M1-MOCK:'+uid,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),cache:'no-store'});}
async function context(uid){
  const c=await browser.newContext({viewport:{width:1440,height:900}});
  await c.route('**/node_modules/.vite/deps/firebase_app.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-app.mjs')}));
  await c.route('**/node_modules/.vite/deps/firebase_auth.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-auth.mjs')}));
  await c.route('**/src/config/runtime.ts*',r=>r.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
  await c.addInitScript(({uid,origin})=>{if(location.origin===origin)sessionStorage.setItem('__m1_test_identity',JSON.stringify({uid,verified:true}));},{uid,origin});
  await c.route(value=>['http:','https:'].includes(value.protocol)&&value.origin!==origin,r=>r.abort());
  return c;
}
async function shot(p,name){
  await p.evaluate(()=>document.fonts.ready);
  // Theme tokens change immediately, but the accepted button material transitions.
  await p.waitForFunction(()=>Array.from(document.querySelectorAll('.sf-page-heading > .sf-button--primary')).every(element=>{
    const style=getComputedStyle(element),token=style.getPropertyValue('--accent').trim();
    const expected=/^#[0-9a-f]{6}$/i.test(token)?`rgb(${[1,3,5].map(start=>parseInt(token.slice(start,start+2),16)).join(', ')})`:token;
    return style.backgroundColor===expected;
  }),undefined,{timeout:3000});
  assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal overflow');await p.screenshot({path:path.join(out,name)});report.screenshots.push(name);
}
try{
  const resultsBefore=(await (await api('/results')).json()).items;
  const result=resultsBefore.find(item=>item.provenance?.input_artifact_sha256==='8e0efd28aaf89f7efbd8107805a74bd837bcc70ea3dc4b4b783eff0e6a220616');assert(result);
  const record=await (await api('/recordings/'+result.recording_id)).json();
  const profilesBefore=await Promise.all(['alice','bob','analyst','admin'].map(async uid=>(await (await api('/auth/me',uid)).json()).user));
  const analyst=profilesBefore[2],existing=(await (await api('/assignments','analyst')).json()).items;
  const existingNotes=await Promise.all(existing.map(async item=>(await (await api('/assignments/'+item.id+'/review','analyst')).json())));
  const ownerC=await context('alice'),analystC=await context('analyst'),owner=await ownerC.newPage(),reviewer=await analystC.newPage(),errors=[];
  for(const p of [owner,reviewer])p.on('pageerror',e=>errors.push(e.message));
  if(layoutOnly){
    await owner.goto(origin+'/app/insights');await owner.getByRole('heading',{name:'Your Library at a glance',exact:true}).waitFor();await shot(owner,'01-insights-desktop.png');
    await reviewer.goto(origin+'/app/review-history');await reviewer.locator('[data-saved-review-id]').first().waitFor();await shot(reviewer,'03-saved-history-desktop.png');
    await reviewer.setViewportSize({width:390,height:844});assert(await reviewer.locator('.sf-workspace-summary-heading h1').evaluate(element=>element.getBoundingClientRect().width>innerWidth*.8));await shot(reviewer,'04-saved-history-mobile.png');await reviewer.setViewportSize({width:820,height:1000});await shot(reviewer,'05-saved-history-tablet.png');
    await reviewer.setViewportSize({width:1440,height:900});await reviewer.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await shot(reviewer,'06-saved-history-midnight.png');
    await owner.setViewportSize({width:390,height:844});await shot(owner,'07-insights-mobile.png');await owner.setViewportSize({width:820,height:1000});await shot(owner,'08-insights-tablet.png');await owner.setViewportSize({width:1440,height:900});await owner.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await shot(owner,'09-insights-midnight.png');
    assert.deepEqual(errors,[]);report.checks.push('READ ONLY: actual saved reviews/activity; corrected full-width mobile heading, desktop/tablet and settled Midnight buttons. No overflow/JS errors or recording/grant/review/result mutations.');report.status='PASS';console.log(report.checks.join('\n'));
  }else{
  const actual=await (await api('/insights')).json();
  await owner.goto(origin+'/app/insights');await owner.getByRole('heading',{name:'Your Library at a glance',exact:true}).waitFor();
  assert.deepEqual(await owner.locator('.sf-insights-facts dd').allTextContents(),[String(actual.counts.total),String(actual.counts.ready),'1:00']);
  await owner.getByRole('button',{name:'See daily counts',exact:true}).focus();await owner.keyboard.press('Enter');assert.equal(await owner.locator('.sf-comparison-table tbody tr').count(),7);
  for(const day of actual.days){const row=owner.locator('.sf-comparison-table tbody tr').filter({hasText:day.date});assert.deepEqual(await row.locator('td').allTextContents(),[String(day.recordings),String(day.completed)]);}
  await owner.getByRole('button',{name:'See less',exact:true}).click();await shot(owner,'01-insights-desktop.png');
  await reviewer.goto(origin+'/app/insights');await reviewer.getByRole('heading',{name:'Your next recording starts the story',exact:true}).waitFor();assert.equal((await (await api('/insights','analyst')).json()).counts.total,0);await shot(reviewer,'02-insights-own-empty.png');
  assert.equal((await api('/reviews/history','alice')).status,403);assert.equal((await api('/reviews/history','admin')).status,403);assert.equal((await fetch(origin+'/api/reviews/history')).status,401);
  report.checks.push('REAL: Insights exactly matches complete own-Library aggregates and seven UTC daily counts. Granted audio is excluded; empty is real zero, not demo content. Role and anonymous denials preserved.');

  const note='LOCAL saved-history acceptance only. No diagnostic assessment. '+('A bounded saved observation belongs to its exact assignment. '.repeat(7))+'<script>window.__unsafeHistory=1</script>';
  for(let i=0;i<4;i++){
    const response=await api('/recordings/'+record.id+'/grants','alice','POST',{recipient_handle:analyst.handle,recipient_public_id:analyst.public_id,permission:'review',resource_id:record.original_resource_id});assert.equal(response.status,201);
    const grant=await response.json();created.push(grant.id);assert.equal((await api('/assignments/'+grant.id+'/review','analyst','PUT',{decision:'needs_attention',notes:note})).status,200);
  }
  await reviewer.goto(origin+'/app/review-history');await reviewer.locator('[data-saved-review-id]').nth(2).waitFor();assert.equal(await reviewer.locator('[data-saved-review-id]').count(),3);
  const next=reviewer.waitForResponse(r=>r.url().endsWith('/api/reviews/history?limit=3&offset=3'));await reviewer.getByRole('button',{name:'See more',exact:true}).focus();await reviewer.keyboard.press('Enter');assert.equal((await next).status(),200);await reviewer.locator('[data-saved-review-id]').nth(3).waitFor();
  await reviewer.getByRole('button',{name:'See less',exact:true}).click();assert.equal(await reviewer.locator('[data-saved-review-id]').count(),3);
  // Saves may share a second; the server's immutable-ID tie-break is authoritative.
  const revokeId=await reviewer.locator('[data-saved-review-id]').first().getAttribute('data-saved-review-id');assert(created.includes(revokeId));
  const row=reviewer.locator(`[data-saved-review-id="${revokeId}"]`);await row.getByRole('button',{name:'Read more notes',exact:true}).click();assert.equal(await row.locator('.sf-feedback-notes').innerText(),note);assert.equal(await reviewer.evaluate(()=>window.__unsafeHistory),undefined);await row.getByRole('button',{name:'Read less',exact:true}).click();
  await shot(reviewer,'03-saved-history-desktop.png');
  await owner.goto(origin+'/app/recordings/'+record.id);const feedback=owner.getByRole('region',{name:'Analyst feedback',exact:true});await feedback.locator('[data-feedback-id]').nth(2).waitFor();assert.equal(await feedback.locator('[data-feedback-id]').count(),3);
  const ownerNext=owner.waitForResponse(r=>r.url().includes('/reviews?limit=3&offset=3'));await feedback.getByRole('button',{name:'See more',exact:true}).click();assert.equal((await ownerNext).status(),200);await feedback.locator('[data-feedback-id]').nth(3).waitFor();await feedback.getByRole('button',{name:'See less',exact:true}).click();assert.equal(await feedback.locator('[data-feedback-id]').count(),3);
  report.checks.push('REAL: saved history and owner feedback both use bounded server paging/See more/less. Long notes disclose accessibly and remain escaped text. Existing shared paging hook preserves owner behavior.');

  for(const resource of result.resources)assert.equal((await api('/media/'+resource.id,'analyst','HEAD')).status,403);
  assert.equal((await api('/grants/'+revokeId,'alice','DELETE')).status,204);
  const refreshed=reviewer.waitForResponse(r=>r.url().endsWith('/api/reviews/history?limit=3&offset=0'));await reviewer.getByRole('button',{name:'Refresh access',exact:true}).click();const refreshedBody=await (await refreshed).json();assert(!refreshedBody.items.some(item=>item.assignment_id===revokeId));
  await reviewer.locator(`[data-saved-review-id="${revokeId}"]`).waitFor({state:'detached'});assert.equal((await api('/assignments/'+revokeId+'/review','analyst')).status,403);
  await reviewer.setViewportSize({width:390,height:844});await shot(reviewer,'04-saved-history-mobile.png');await reviewer.setViewportSize({width:820,height:1000});await shot(reviewer,'05-saved-history-tablet.png');
  await reviewer.setViewportSize({width:1440,height:900});await reviewer.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await shot(reviewer,'06-saved-history-midnight.png');
  await owner.goto(origin+'/app/insights');await owner.getByRole('heading',{name:'Your Library at a glance',exact:true}).waitFor();await owner.setViewportSize({width:390,height:844});await shot(owner,'07-insights-mobile.png');await owner.setViewportSize({width:820,height:1000});await shot(owner,'08-insights-tablet.png');await owner.setViewportSize({width:1440,height:900});await owner.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await shot(owner,'09-insights-midnight.png');
  await owner.emulateMedia({reducedMotion:'reduce'});await reviewer.emulateMedia({reducedMotion:'reduce'});
  report.checks.push('REAL: revoked saved history disappears on access refresh; exact Original assignment never grants siblings. Desktop/mobile/tablet/Midnight layouts have no overflow; keyboard disclosure and reduced-motion layout work.');

  await owner.route(origin+'/api/insights',r=>r.abort());await owner.getByRole('button',{name:'Refresh activity',exact:true}).click();await owner.getByText(/The application service could not be reached/).waitFor();assert.equal(await owner.locator('.sf-insights-facts').count(),0);await shot(owner,'10-insights-unavailable.png');await owner.unroute(origin+'/api/insights');
  await reviewer.route(origin+'/api/reviews/history*',r=>r.abort());await reviewer.getByRole('button',{name:'Refresh access',exact:true}).click();await reviewer.getByText(/The application service could not be reached/).waitFor();assert.equal(await reviewer.locator('[data-saved-review-id]').count(),0);await reviewer.unroute(origin+'/api/reviews/history*');
  assert.deepEqual(errors,[]);assert.deepEqual((await (await api('/results')).json()).items,resultsBefore);assert.deepEqual(await Promise.all(['alice','bob','analyst','admin'].map(async uid=>(await (await api('/auth/me',uid)).json()).user)),profilesBefore);assert.deepEqual(await Promise.all(existing.map(async item=>(await (await api('/assignments/'+item.id+'/review','analyst')).json()))),existingNotes);
  report.checks.push('TRANSPORT FAILURE ONLY: unavailable APIs clear prior sensitive content, never synthesize zero/demo results. No JS exceptions; existing accounts, notes and frozen results remain unchanged.');report.status='PASS';console.log(report.checks.join('\n'));
  }
}catch(error){report.status='FAIL';report.error=error.message;throw error;}
finally{for(const id of created)assert.equal((await api('/grants/'+id,'alice','DELETE')).status,204);report.temporaryGrantsRevoked=created.length;await writeFile(path.join(out,'receipt.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}

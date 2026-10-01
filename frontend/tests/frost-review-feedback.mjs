// Real LOCAL API/SQLite/private HLS files. Only identity SDK/verifier are TEST ONLY.
// Never attach to the owner's headed browsers or change existing assignments/notes.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import path from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';

const layoutOnly=process.argv.includes('--layout-only');
const origin='http://127.0.0.1:4200',out=path.resolve('output/playwright/review-feedback/'+(layoutOnly?'final-layout-v6':'v2'));
await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true});
const report={checks:[],screenshots:[],identity:'Fixed fictional SDK/verifier; real local recording/grant/review/media APIs. No live Firebase.'},created=[];
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
  // Wait for the actual control material to settle, not unrelated owl animations.
  await p.waitForFunction(()=>Array.from(document.querySelectorAll('.sf-greeting-actions .sf-button--secondary,.sf-owner-feedback .sf-button--secondary')).every(element=>{
    const style=getComputedStyle(element),token=style.getPropertyValue('--control-surface').trim();
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
  const ownerC=await context('alice'),analystC=await context('analyst');
  const owner=await ownerC.newPage(),reviewer=await analystC.newPage(),errors=[];
  for(const p of [owner,reviewer])p.on('pageerror',e=>errors.push(e.message));
  await owner.goto(origin+'/app/overview');await owner.getByRole('heading',{name:'Recent recordings',exact:true}).waitFor();assert.equal(await owner.locator('.sf-greeting .sf-button--primary').innerText(),'New recording');
  assert.equal(await owner.getByRole('heading',{name:'Your assigned work',exact:true}).count(),0);await shot(owner,'01-staff-overview-desktop.png');
  await reviewer.goto(origin+'/app/overview');await reviewer.getByRole('heading',{name:'Your assigned work',exact:true}).waitFor();assert.equal(await reviewer.locator('.sf-greeting .sf-button--primary').innerText(),'Open assigned reviews');assert.equal(await reviewer.getByRole('link',{name:'New recording',exact:true}).count(),1);
  if(layoutOnly){
    await shot(reviewer,'02-analyst-overview-desktop.png');
    await owner.goto(origin+'/app/recordings/'+record.id);const feedback=owner.getByRole('region',{name:'Analyst feedback',exact:true});await feedback.getByRole('button',{name:'Refresh feedback',exact:true}).waitFor();
    const align=()=>feedback.evaluate(el=>window.scrollTo({top:scrollY+el.getBoundingClientRect().top-84,behavior:'instant'}));
    await align();await shot(owner,'03-owner-feedback-desktop.png');
    await owner.setViewportSize({width:390,height:844});await align();await shot(owner,'05-owner-feedback-mobile.png');
    await reviewer.setViewportSize({width:390,height:844});await shot(reviewer,'06-analyst-overview-mobile.png');
    await reviewer.setViewportSize({width:820,height:1000});await shot(reviewer,'07-analyst-overview-tablet.png');
    await owner.setViewportSize({width:1440,height:900});await owner.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await align();await shot(owner,'08-owner-feedback-midnight.png');
    await reviewer.setViewportSize({width:1440,height:900});await reviewer.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await shot(reviewer,'09-analyst-overview-midnight.png');
    await owner.emulateMedia({reducedMotion:'reduce'});await reviewer.emulateMedia({reducedMotion:'reduce'});assert.deepEqual(errors,[]);
    assert.deepEqual(await Promise.all(existing.map(async item=>(await (await api('/assignments/'+item.id+'/review','analyst')).json()))),existingNotes);
    report.checks.push('READ ONLY: final actual Staff/Analyst priorities, saved owner feedback/current exact assignments; desktop/mobile/tablet/Midnight, no overflow/JS errors; existing saved notes unchanged. No grants, notes, jobs or results mutated.');report.status='PASS';console.log(report.checks.join('\n'));
  }else{
  assert.equal((await api('/assignments','alice')).status,403);
  report.checks.push('REAL: Staff primary is New recording; Analyst primary is Open assigned reviews, retaining own uploads. Existing analyst role-only assignment policy unchanged.');

  await owner.goto(origin+'/app/recordings/'+record.id);
  const feedback=owner.getByRole('region',{name:'Analyst feedback',exact:true});await feedback.getByRole('button',{name:'Refresh feedback',exact:true}).waitFor();
  await feedback.getByRole('button',{name:'Request review',exact:true}).click();assert.equal(await owner.locator('.sf-owner-tools').getAttribute('open'),'');
  const handle=owner.getByRole('textbox',{name:'Share with @username',exact:true});assert(await handle.evaluate(el=>el===document.activeElement));await handle.fill('@'+analyst.handle);
  await owner.getByRole('button',{name:'Find person',exact:true}).click();await owner.getByRole('combobox',{name:'Permission',exact:true}).selectOption('review');await owner.getByRole('combobox',{name:'What can they access?',exact:true}).selectOption(record.original_resource_id);
  const assigned=owner.waitForResponse(r=>r.url()===origin+'/api/recordings/'+record.id+'/grants'&&r.request().method()==='POST');await owner.getByRole('button',{name:'Share access',exact:true}).click();const granted=await assigned;assert.equal(granted.status(),201);const grant=await granted.json();created.push(grant.id);
  await feedback.getByRole('button',{name:'Refresh feedback',exact:true}).waitFor();
  // Latest saved history precedes pending work; do not assume an empty owner account.
  for(let i=0;i<10&&!await feedback.locator(`[data-feedback-id="${grant.id}"]`).count();i++){
    const next=owner.waitForResponse(r=>r.url().includes('/reviews?limit=3&offset=')&&!r.url().endsWith('offset=0'));
    await feedback.getByRole('button',{name:'See more',exact:true}).click();const page=await (await next).json();assert(page.items.length);
    await feedback.locator(`[data-feedback-id="${page.items.at(-1).assignment_id}"]`).waitFor();
  }
  await feedback.locator(`[data-feedback-id="${grant.id}"]`).waitFor();
  report.checks.push('REAL: owner Request review focuses existing @handle sharing; exact Analyst review POST persists and owner sees actual pending assignment. No new granting rule.');

  await reviewer.goto(origin+'/app/reviews/'+grant.id);
  await reviewer.locator('.sf-player[data-media-state="ready"]').waitFor();assert.equal(await reviewer.locator('.sf-player').count(),1);
  const notes=reviewer.getByRole('textbox',{name:'Review notes',exact:true});assert((await notes.getAttribute('aria-describedby')));
  const note='LOCAL feedback workflow acceptance only. No diagnostic assessment. '+('Saved observations remain part of the owner’s recording history. '.repeat(7))+'<script>window.__unsafeFeedback=1</script>';
  await notes.fill(note);await reviewer.getByRole('combobox',{name:'Review outcome',exact:true}).selectOption('needs_attention');
  const saved=reviewer.waitForResponse(r=>r.url()===origin+'/api/assignments/'+grant.id+'/review'&&r.request().method()==='PUT');await reviewer.getByRole('button',{name:'Save review',exact:true}).click();assert.equal((await saved).status(),200);await reviewer.getByText('Review saved.',{exact:true}).waitFor();
  await reviewer.getByRole('region',{name:'Your review',exact:true}).scrollIntoViewIfNeeded();await shot(reviewer,'02-analyst-saved-review-desktop.png');
  await feedback.getByRole('button',{name:'Refresh feedback',exact:true}).click();const savedRow=feedback.locator(`[data-feedback-id="${grant.id}"]`);await savedRow.getByText('Needs attention',{exact:true}).waitFor();
  await savedRow.getByRole('button',{name:'Read more notes',exact:true}).focus();await owner.keyboard.press('Space');assert.equal(await savedRow.locator('.sf-feedback-notes').innerText(),note);assert.equal(await owner.evaluate(()=>window.__unsafeFeedback),undefined);await savedRow.getByRole('button',{name:'Read less',exact:true}).click();
  assert((await savedRow.innerText()).includes('@'+analyst.handle));
  await owner.reload();await feedback.locator(`[data-feedback-id="${grant.id}"]`).getByText('Needs attention',{exact:true}).waitFor();
  const freshC=await context('alice'),fresh=await freshC.newPage();await fresh.goto(origin+'/app/recordings/'+record.id);await fresh.locator(`[data-feedback-id="${grant.id}"]`).waitFor();assert((await fresh.locator(`[data-feedback-id="${grant.id}"] .sf-feedback-notes`).innerText()).startsWith('LOCAL feedback workflow'));await freshC.close();
  report.checks.push('REAL: Analyst saves actual outcome/notes; owner reads exact reviewer identity/source/time, refresh and new session persist. Long-note keyboard disclosure works; script text is escaped, never executed.');

  for(let i=0;i<3;i++){const r=await api('/recordings/'+record.id+'/grants','alice','POST',{recipient_handle:analyst.handle,recipient_public_id:analyst.public_id,permission:'review',resource_id:record.original_resource_id});assert.equal(r.status,201);created.push((await r.json()).id);}
  await feedback.getByRole('button',{name:'Refresh feedback',exact:true}).click();await feedback.getByRole('button',{name:'See more',exact:true}).waitFor();assert.equal(await feedback.locator('[data-feedback-id]').count(),3);
  const moreResponse=owner.waitForResponse(r=>r.url().includes('/reviews?limit=3&offset=3'));await feedback.getByRole('button',{name:'See more',exact:true}).focus();await owner.keyboard.press('Enter');assert.equal((await moreResponse).status(),200);await feedback.locator('[data-feedback-id]').nth(3).waitFor();assert((await feedback.locator('[data-feedback-id]').count())>3);
  await feedback.getByRole('button',{name:'See less',exact:true}).click();assert.equal(await feedback.locator('[data-feedback-id]').count(),3);await feedback.evaluate(el=>el.scrollIntoView({block:'start'}));await shot(owner,'03-owner-feedback-desktop.png');
  await reviewer.goto(origin+'/app/overview');await reviewer.locator('.sf-assignment-list li').first().waitFor();assert.equal(await reviewer.locator('.sf-assignment-list li').count(),3);assert(!(await reviewer.locator('.sf-assignment-list').innerText()).includes('Needs attention'),'Pending assignments prioritized above saved review');await shot(reviewer,'04-analyst-overview-desktop.png');
  report.checks.push('REAL: owner feedback is three rows with bounded API See more/less, not an unbounded receipt. Analyst Overview prioritizes current pending work and scoped actual counts.');

  await owner.setViewportSize({width:390,height:844});await feedback.evaluate(el=>el.scrollIntoView({block:'start'}));await shot(owner,'05-owner-feedback-mobile.png');
  await reviewer.setViewportSize({width:390,height:844});await reviewer.goto(origin+'/app/overview');await reviewer.locator('.sf-assignment-list').waitFor();await shot(reviewer,'06-analyst-overview-mobile.png');
  await reviewer.setViewportSize({width:820,height:1000});await shot(reviewer,'07-analyst-overview-tablet.png');
  await owner.setViewportSize({width:1440,height:900});await owner.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await feedback.evaluate(el=>el.scrollIntoView({block:'start'}));await shot(owner,'08-owner-feedback-midnight.png');
  await owner.emulateMedia({reducedMotion:'reduce'});await reviewer.emulateMedia({reducedMotion:'reduce'});assert.equal(await owner.locator('.sf-app').getAttribute('data-theme'),'midnight');
  report.checks.push('REAL: desktop/mobile/tablet/Midnight, readable notes/outcome/reference wrapping and no horizontal overflow; keyboard controls/reduced-motion layout preserved.');

  const feedbackURL='/recordings/'+record.id+'/reviews';
  for(const uid of ['bob','analyst','admin'])assert.equal((await api(feedbackURL,uid)).status,403);assert.equal((await fetch(origin+'/api'+feedbackURL)).status,401);
  for(const resource of result.resources)assert.equal((await api('/media/'+resource.id,'analyst','HEAD')).status,403);
  assert.equal((await api('/grants/'+grant.id,'alice','DELETE')).status,204);
  await reviewer.goto(origin+'/app/reviews/'+grant.id);await reviewer.getByText(/You do not have permission/).waitFor();assert.equal(await reviewer.locator('.sf-review-editor,.sf-player').count(),0);
  assert.equal((await api('/assignments/'+grant.id+'/review','analyst','PUT',{decision:'accepted',notes:'Not permitted'})).status,403);
  await feedback.getByRole('button',{name:'Refresh feedback',exact:true}).click();await feedback.locator(`[data-feedback-id="${grant.id}"]`).getByText('Access revoked',{exact:true}).waitFor();
  const ownerPage=await (await api(feedbackURL)).json();assert.equal(ownerPage.items.find(item=>item.assignment_id===grant.id).notes,note);
  report.checks.push('REAL: unrelated Staff, nonowner Admin, reviewer and anonymous cannot read owner feedback. Exact Original review never exposes Heart/Lung. Revocation denies reviewer read/write; owner retains saved annotation history.');

  await owner.route(origin+'/api/recordings/'+record.id+'/reviews*',r=>r.abort());await feedback.getByRole('button',{name:'Refresh feedback',exact:true}).click();await feedback.getByText(/The application service could not be reached/).waitFor();assert.equal(await feedback.locator('[data-feedback-id]').count(),0);await shot(owner,'09-feedback-unavailable.png');await owner.unroute(origin+'/api/recordings/'+record.id+'/reviews*');
  assert.deepEqual((await (await api('/results')).json()).items,resultsBefore,'No model/result mutation');
  assert.deepEqual(await Promise.all(['alice','bob','analyst','admin'].map(async uid=>(await (await api('/auth/me',uid)).json()).user)),profilesBefore);
  assert.deepEqual(await Promise.all(existing.map(async item=>(await (await api('/assignments/'+item.id+'/review','analyst')).json()))),existingNotes,'Existing owner notes/assignments preserved');
  assert.deepEqual(errors,[]);report.checks.push('TRANSPORT FAILURE ONLY: unavailable feedback clears old private rows; no fake fallback. Existing accounts/assignments/notes/results unchanged; no JS exceptions.');report.status='PASS';console.log(report.checks.join('\n'));
  }
}catch(error){report.status='FAIL';report.error=error.message;throw error;}
finally{for(const id of created)assert.equal((await api('/grants/'+id,'alice','DELETE')).status,204);report.temporaryGrantsRevoked=created.length;await writeFile(path.join(out,'receipt.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}

import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';

const base=process.env.FRONTEND_URL||'http://127.0.0.1:4180';
const output=path.resolve('evidence/winter-glass/admin');await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1,permissions:['clipboard-read','clipboard-write']});
const page=await context.newPage();const errors=[];const requests=[];const checks=[];
page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)requests.push({url:r.url(),status:r.status()});});
const visit=async(route)=>{await page.goto(base+route);await page.locator('main h1').waitFor();};
const screenshot=async(name)=>page.screenshot({path:path.join(output,name+'.png'),fullPage:true});
const check=async(name,fn)=>{try{await fn();checks.push({name,status:'PASS'});console.log('PASS',name);}catch(e){checks.push({name,status:'FAIL',error:e.message});await screenshot('failure-'+checks.length).catch(()=>{});throw e;}};
const save=async()=>{await page.getByRole('button',{name:'Save changes',exact:true}).click();await page.getByText('All changes saved',{exact:true}).waitFor();};
async function signIn(name){await page.goto(base+'/login#demo-personas');await page.getByRole('button',{name:new RegExp(name)}).click();await page.waitForURL(/\/app\//);await page.locator('.app-shell').waitFor();await page.locator('.workspace h1').waitFor();}
const storedState=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('stethofuse-demo-v1')));
async function selectPersona(id,route){await page.evaluate(id=>sessionStorage.setItem('stethofuse-demo-persona',id),id);await visit(route);}
try{
 await signIn('Elias Noor');
 await check('Administrator overview is fictional metadata and renders',async()=>{assert.match(await page.locator('main').innerText(),/Fictional demonstration/);await screenshot('overview-desktop');});
 await check('User ID search, provider/role/status/date filters, sort and copy',async()=>{
  await visit('/app/admin/users');await page.getByLabel('Name, email or User ID').fill('USR-1002');assert.equal(await page.locator('tbody tr').count(),1);assert.match(await page.locator('tbody').innerText(),/Daniel Tan/);
  await page.getByRole('button',{name:'Copy USR-1002'}).click();assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),'USR-1002');await screenshot('user-id-filter-desktop');
  await page.getByRole('button',{name:'Clear filters'}).click();await page.getByLabel('Role',{exact:true}).selectOption('analyst');assert.equal(await page.locator('tbody tr').count(),1);
  await page.getByRole('button',{name:'Clear filters'}).click();await page.getByLabel('Provider',{exact:true}).selectOption('google');await page.getByLabel('Joined from').fill('2026-08-01');await page.getByLabel('Sort',{exact:true}).selectOption('id');assert.equal(await page.locator('tbody tr').count(),1);assert.match(await page.locator('tbody').innerText(),/USR-1002/);
 });
 await check('User pagination changes the visible directory rows',async()=>{
  await page.getByRole('button',{name:'Clear filters'}).click();assert.equal(await page.locator('tbody tr').count(),5);await page.getByRole('button',{name:'Next',exact:true}).click();assert.equal(await page.locator('tbody tr').count(),1);await page.getByRole('button',{name:'Previous',exact:true}).click();assert.equal(await page.locator('tbody tr').count(),5);
 });
 await check('Confirmed role/status change persists and is audited',async()=>{
  await visit('/app/admin/users/USR-1004');await page.getByLabel('Application role').selectOption('analyst');await page.getByLabel('Account status',{exact:true}).selectOption('active');await page.getByRole('button',{name:'Review changes'}).click();assert.equal(await page.locator('dialog[open]').count(),1);await page.getByRole('button',{name:'Confirm changes',exact:true}).click();await page.reload();assert.equal(await page.getByLabel('Application role').inputValue(),'analyst');assert.equal(await page.getByLabel('Account status',{exact:true}).inputValue(),'active');assert.match(await page.locator('main').innerText(),/Account updated/);
 });
 await check('Last active administrator cannot be disabled',async()=>{
  await visit('/app/admin/users/USR-3001');await page.getByLabel('Account status',{exact:true}).selectOption('disabled');await page.getByRole('button',{name:'Review changes'}).click();await page.getByRole('button',{name:'Confirm changes',exact:true}).click();await page.locator('dialog[open]').getByText('The last active administrator cannot be disabled or demoted.',{exact:true}).waitFor();await screenshot('last-admin-protection');await page.locator('dialog[open]').getByRole('button',{name:'Cancel',exact:true}).click();await page.locator('.save-bar').getByRole('button',{name:'Cancel',exact:true}).click();
 });
 const originalSummary='Sofia original completed research review. Preserve authorship.';
 const originalNote='Original analyst observation at one second.';
 let originalReview,replacementId;
 await check('Explicit review access permits recording and results but keeps processing jobs owner-scoped',async()=>{
  await selectPersona('USR-2001','/app/recordings/REC-1042');await page.getByRole('button',{name:'Play original',exact:true}).waitFor();
  assert.equal(await page.locator('a[href^="/app/processing/"]').count(),0);assert.equal(await page.getByRole('button',{name:'Request ensemble run',exact:true}).count(),0);
  await visit('/app/results/RES-3100');await page.getByRole('button',{name:'Play heart',exact:true}).waitFor();
  await visit('/app/processing/JOB-2100');await page.getByRole('heading',{name:'This recording is private.',exact:true}).waitFor();assert.match(await page.locator('main').innerText(),/Processing jobs are visible only to their owner/);assert.equal(await page.getByRole('heading',{name:'Processing timeline',exact:true}).count(),0);
  await selectPersona('USR-1001','/app/processing/JOB-2100');await page.getByRole('heading',{name:'Your demo outputs are ready.',exact:true}).waitFor();await page.getByRole('link',{name:'Open result',exact:true}).waitFor();
 });
 await check('The current analyst cannot be selected again and the saved review remains unchanged',async()=>{
  await selectPersona('USR-2001','/app/reviews/ASN-401');
  await page.getByLabel('Time in seconds',{exact:true}).fill('1');await page.getByLabel('Observation',{exact:true}).fill(originalNote);await page.getByRole('button',{name:'Add note',exact:true}).click();
  await page.getByLabel('Review summary').fill(originalSummary);await page.getByRole('button',{name:'Submit review',exact:true}).click();await page.locator('dialog[open]').getByRole('button',{name:'Submit decision',exact:true}).click();await page.locator('dialog[open]').waitFor({state:'hidden'});
  const before=await storedState();originalReview=before.reviews.find(r=>r.assignmentId==='ASN-401');assert.equal(originalReview.authorId,'USR-2001');assert.equal(originalReview.decision,'reviewed');
  await selectPersona('USR-3001','/app/admin/assignments');await page.locator('tbody tr').filter({hasText:'ASN-401'}).getByRole('button',{name:'Reassign',exact:true}).click();
  assert.equal(await page.getByLabel('Active analyst').locator('option[value="USR-2001"]').count(),0);
  assert.equal(await page.getByLabel('Active analyst').inputValue(),'');assert.equal(await page.getByRole('button',{name:'Confirm assignment',exact:true}).isDisabled(),true);
  const after=await storedState();assert.deepEqual(after.assignments,before.assignments);assert.deepEqual(after.reviews,before.reviews);assert.deepEqual(after.audit,before.audit);
  await page.locator('dialog[open]').getByRole('button',{name:'Cancel',exact:true}).click();
 });
 await check('Reassignment revokes the old ID and creates a new pending grant with the correct notification',async()=>{
  await page.locator('tbody tr').filter({hasText:'ASN-401'}).getByRole('button',{name:'Reassign',exact:true}).click();await page.getByLabel('Active analyst').selectOption('USR-1004');await page.getByRole('button',{name:'Confirm assignment',exact:true}).click();await page.locator('dialog[open]').waitFor({state:'hidden'});
  const current=await storedState(),original=current.assignments.find(a=>a.id==='ASN-401');
  const replacement=current.assignments.find(a=>a.recordingId==='REC-1042'&&a.analystId==='USR-1004'&&a.status==='pending');assert.ok(replacement);replacementId=replacement.id;
  assert.notEqual(replacementId,'ASN-401');assert.equal(original.analystId,'USR-2001');assert.equal(original.status,'revoked');assert.equal(replacement.permission,'review');assert.equal(replacement.ownerId,'USR-1001');
  assert.deepEqual(current.reviews.find(r=>r.assignmentId==='ASN-401'),originalReview);assert.equal(current.reviews.some(r=>r.assignmentId===replacementId),false);
  assert.equal(current.drafts[`USR-1004:review:${replacementId}`],undefined);
  assert.ok(current.notifications.some(n=>n.userId==='USR-1004'&&n.title==='A recording was assigned to you'&&n.href===`/app/reviews/${replacementId}`));
  assert.ok(current.notifications.some(n=>n.userId==='USR-2001'&&n.title==='Recording access was reassigned'&&n.href==='/app/shared'));
  await page.reload();assert.match(await page.locator('tbody tr').filter({hasText:'ASN-401'}).innerText(),/Sofia Chen/);assert.match(await page.locator('tbody tr').filter({hasText:'ASN-401'}).innerText(),/revoked/i);
  assert.match(await page.locator('tbody tr').filter({hasText:replacementId}).innerText(),/Noah Idris/);await screenshot('assignment-preserved-history');
 });
 await check('A duplicate active recipient cannot receive another replacement assignment',async()=>{
  const before=await storedState();await page.locator('tbody tr').filter({hasText:'ASN-401'}).getByRole('button',{name:'Create new assignment',exact:true}).click();await page.getByLabel('Active analyst').selectOption('USR-1004');await page.getByRole('button',{name:'Confirm assignment',exact:true}).click();
  await page.locator('dialog[open]').getByText('This analyst already has an active assignment for this recording.',{exact:true}).waitFor();const after=await storedState();assert.deepEqual(after.assignments,before.assignments);assert.deepEqual(after.reviews,before.reviews);
  await page.locator('dialog[open]').getByRole('button',{name:'Cancel',exact:true}).click();
 });
 await check('Replacement reviewer starts empty and cannot overwrite the former author review',async()=>{
  await selectPersona('USR-1004',`/app/reviews/${replacementId}`);assert.equal(await page.getByLabel('Review summary').inputValue(),'');assert.equal(await page.getByText(originalNote,{exact:true}).count(),0);assert.equal(await page.locator('.timestamp-note').count(),0);
  await page.getByLabel('Time in seconds',{exact:true}).fill('2');await page.getByLabel('Observation',{exact:true}).fill('Replacement analyst independent observation.');await page.getByRole('button',{name:'Add note',exact:true}).click();await page.getByLabel('Review summary').fill('Noah independent research review.');await page.getByRole('button',{name:'Save draft',exact:true}).click();
  await page.waitForFunction(id=>JSON.parse(localStorage.getItem('stethofuse-demo-v1')).reviews.some(r=>r.assignmentId===id&&r.authorId==='USR-1004'),replacementId);
  await page.reload();assert.equal(await page.getByLabel('Review summary').inputValue(),'Noah independent research review.');assert.equal(await page.getByText(originalNote,{exact:true}).count(),0);
  const current=await storedState();assert.deepEqual(current.reviews.find(r=>r.assignmentId==='ASN-401'),originalReview);const replacementReview=current.reviews.find(r=>r.assignmentId===replacementId);assert.notEqual(replacementReview.id,originalReview.id);assert.equal(replacementReview.authorId,'USR-1004');assert.equal(replacementReview.notes.length,1);
  await screenshot('replacement-review-independent');await selectPersona('USR-2001','/app/reviews/ASN-401');await page.getByRole('heading',{name:'This recording is private.',exact:true}).waitFor();assert.equal(await page.getByLabel('Review summary').count(),0);
  await visit('/app/recordings/REC-1042');await page.getByRole('heading',{name:'This recording is private.',exact:true}).waitFor();
  await visit('/app/review-history');assert.match(await page.locator('tbody tr').filter({hasText:'ASN-401'}).innerText(),/revoked/i);
 });
 await check('Replacement revocation and both assignment audit IDs persist without removing review history',async()=>{
  await selectPersona('USR-3001','/app/admin/assignments');const row=page.locator('tbody tr').filter({hasText:replacementId});await row.getByRole('button',{name:'Revoke',exact:true}).click();await page.getByRole('button',{name:'Revoke access',exact:true}).click();await page.reload();assert.match(await page.locator('tbody tr').filter({hasText:replacementId}).innerText(),/revoked/i);
  const current=await storedState();assert.deepEqual(current.reviews.find(r=>r.assignmentId==='ASN-401'),originalReview);assert.ok(current.reviews.some(r=>r.assignmentId===replacementId&&r.authorId==='USR-1004'));
  await visit('/app/admin/audit');await page.getByLabel('Event, actor, target ID or action').fill('ASN-401');assert.match(await page.locator('tbody').innerText(),/Access revoked/);
  await page.getByLabel('Event, actor, target ID or action').fill(replacementId);assert.match(await page.locator('tbody').innerText(),/Assignment changed/);assert.match(await page.locator('tbody').innerText(),/Access revoked/);
  await page.locator('tbody tr').filter({hasText:'Access revoked'}).getByRole('button',{name:'Details'}).click();await page.locator('dialog[open]').getByText('Content access removed immediately.',{exact:true}).waitFor();await page.locator('dialog[open]').getByRole('button',{name:'Close dialog'}).click();await screenshot('assignment-audit');
 });
 await check('Global records show metadata without private audio controls',async()=>{
  await visit('/app/admin/records');await page.getByLabel('Recording ID or owner ID').fill('REC-1042');assert.equal(await page.locator('tbody tr').count(),1);await page.getByRole('button',{name:'Job metadata'}).click();assert.match(await page.locator('dialog[open]').innerText(),/JOB-2100/);assert.equal(await page.locator('audio').count(),0);assert.equal(await page.getByRole('button',{name:/Play original|Download original/}).count(),0);await page.locator('dialog[open]').getByRole('button',{name:'Close dialog'}).click();
 });
 await check('Ensemble experiment saves label only with honest attribution',async()=>{
  await visit('/app/admin/ensemble');assert.match(await page.locator('main').innerText(),/Paper title, authors/);await page.getByLabel('Demonstration fusion configuration').selectOption('Adaptive fusion · experiment planned');await page.getByRole('button',{name:'Review configuration'}).click();await page.getByRole('button',{name:'Save demo configuration'}).click();await page.reload();assert.equal(await page.getByLabel('Demonstration fusion configuration').inputValue(),'Adaptive fusion · experiment planned');await screenshot('ensemble-provenance');
 });
 await check('System settings validate and persist without deployment mutation',async()=>{
  await visit('/app/admin/settings');await page.getByLabel('Maximum WAV upload size (MB)').fill('0');await page.getByRole('button',{name:'Review settings'}).click();await page.getByText('Enter an upload limit from 1 to 250 MB.',{exact:true}).first().waitFor();await page.getByLabel('Maximum WAV upload size (MB)').fill('25');await page.getByLabel('Presented retention period (days)').fill('180');await page.getByRole('button',{name:'Review settings'}).click();await page.getByRole('button',{name:'Save demo preferences'}).click();await page.reload();assert.equal(await page.getByLabel('Maximum WAV upload size (MB)').inputValue(),'25');
 });
 await check('Profile save/cancel persists only editable name',async()=>{
  await visit('/app/profile');await page.getByLabel('Display name').fill('Elias Noor Demo');await save();await page.reload();assert.equal(await page.getByLabel('Display name').inputValue(),'Elias Noor Demo');assert.equal(await page.getByLabel('Email',{exact:true}).getAttribute('readonly'),'');await page.getByLabel('Display name').fill('Discard this name');await page.locator('.save-bar').getByRole('button',{name:'Cancel'}).click();assert.equal(await page.getByLabel('Display name').inputValue(),'Elias Noor Demo');
 });
 await check('Unsaved profile changes block route navigation and can be discarded',async()=>{
  await page.getByLabel('Display name').fill('Unsaved name');await page.getByRole('link',{name:'Manage account security'}).click();await page.getByRole('button',{name:'Stay here'}).click();assert.equal(await page.getByLabel('Display name').inputValue(),'Unsaved name');await page.getByRole('link',{name:'Manage account security'}).click();await page.getByRole('button',{name:'Discard and leave'}).click();await page.waitForURL(/\/app\/settings/);await visit('/app/profile');assert.equal(await page.getByLabel('Display name').inputValue(),'Elias Noor Demo');
 });
 await check('General settings and unsaved section confirmation',async()=>{
  await visit('/app/settings');await page.getByLabel('Timezone',{exact:true}).selectOption('UTC');await page.getByLabel('Date format').selectOption('iso');await page.getByRole('button',{name:'Appearance',exact:true}).click();await page.getByRole('button',{name:'Keep editing',exact:true}).click();assert.equal(await page.getByLabel('Timezone',{exact:true}).inputValue(),'UTC');await save();await page.reload();assert.equal(await page.getByLabel('Timezone',{exact:true}).inputValue(),'UTC');assert.equal(await page.getByLabel('Date format').inputValue(),'iso');
 });
 await check('Appearance reduced motion/snow/contrast save, cancel and refresh',async()=>{
  await page.getByRole('button',{name:'Appearance',exact:true}).click();await page.getByLabel('Reduce nonessential motion').check();await page.getByLabel('Show delicate snow').uncheck();await page.getByLabel('Increase interface contrast').check();await save();await page.reload();assert.equal(await page.getByLabel('Reduce nonessential motion').isChecked(),true);assert.equal(await page.getByLabel('Show delicate snow').isChecked(),false);assert.equal(await page.locator('.app-shell.high-contrast.reduce-motion').count(),1);await screenshot('settings-appearance-desktop');
 });
 await check('Notification preferences persist without external delivery',async()=>{
  await page.getByRole('button',{name:'Notifications',exact:true}).click();await page.getByLabel('Email preference').check();await page.getByLabel('Processing updates').uncheck();await save();await page.reload();assert.equal(await page.getByLabel('Email preference').isChecked(),true);assert.equal(await page.getByLabel('Processing updates').isChecked(),false);assert.match(await page.locator('main').innerText(),/No transactional email provider/);
 });
 await check('Recording input/metadata/playback defaults persist',async()=>{
  await page.getByRole('button',{name:'Recording defaults',exact:true}).click();await page.getByLabel('Preferred input').selectOption('Browser default input');await page.getByLabel('Default position').selectOption('Standing');await page.getByLabel('Playback speed').selectOption('0.75');await save();await page.reload();assert.equal(await page.getByLabel('Default position').inputValue(),'Standing');assert.equal(await page.getByLabel('Playback speed').inputValue(),'0.75');
 });
 await check('Data export is scoped and deletion request does not claim deletion',async()=>{
  await page.getByRole('button',{name:'Data & storage',exact:true}).click();await page.getByRole('button',{name:'Export',exact:true}).click();const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Download JSON'}).click();const download=await downloadPromise;const downloadPath=path.join(output,'demo-metadata-export.json');await download.saveAs(downloadPath);const data=JSON.parse(await fs.readFile(downloadPath,'utf8'));assert.equal(data.profile.id,'USR-3001');assert.ok(data.recordings.every(r=>r.ownerId==='USR-3001'));assert.equal(data.demo,true);await page.getByRole('button',{name:'Request deletion'}).click();assert.equal(await page.getByRole('button',{name:'Record demo request'}).isDisabled(),true);await page.getByLabel('Type DELETE to confirm the demo request').fill('DELETE');await page.getByRole('button',{name:'Record demo request'}).click();await page.getByText('Demo request recorded. No external action taken.',{exact:true}).waitFor();
 });
 await check('Security provider, linking and reauth remain honest unavailable states',async()=>{
  await page.getByRole('button',{name:'Security',exact:true}).click();await page.getByRole('button',{name:'Review status',exact:true}).click();await page.getByText('Authentication integration unavailable',{exact:true}).waitFor();await page.getByRole('button',{name:'Understood'}).click();await page.getByRole('button',{name:'Review linking'}).click();await page.getByText('No account was linked',{exact:true}).waitFor();await page.getByRole('button',{name:'Understood'}).click();assert.equal(await page.locator('input[type=password]').count(),0);
 });
 await check('Notifications read/unread persistence and authorized navigation',async()=>{
  await visit('/app/notifications');await page.getByRole('button',{name:'Mark all as read'}).click();await page.getByRole('tab',{name:/Unread/}).click();await page.getByRole('heading',{name:'You’re all caught up'}).waitFor();await page.getByRole('tab',{name:/All updates/}).click();await page.getByRole('button',{name:'Mark unread',exact:true}).first().click();await page.reload();await page.locator('.notification-item').first().waitFor();assert.equal(await page.locator('.notification-item.unread').count(),1);assert.match(await page.getByRole('link',{name:'Open workspace'}).first().getAttribute('href'),/^\/app\//);
 });
 await check('Help search, disclosure and support template',async()=>{
  await visit('/app/help');await page.getByLabel('Search help').fill('WAV');assert.ok(await page.locator('details').count()>=1);await page.locator('details summary').first().click();assert.equal(await page.locator('details[open]').count(),1);await page.getByRole('button',{name:'Copy safe report template'}).click();assert.match(await page.evaluate(()=>navigator.clipboard.readText()),/No passwords, reset links/);
 });
 await check('Account-specific preferences do not leak to Staff A',async()=>{
  await page.getByRole('button',{name:'Switch demo account'}).click();await page.locator('dialog[open]').getByRole('button',{name:/Amina Rahman/}).click();await visit('/app/settings');assert.equal(await page.getByLabel('Timezone',{exact:true}).inputValue(),'Asia/Kuala_Lumpur');await page.getByRole('button',{name:'Appearance',exact:true}).click();assert.equal(await page.getByLabel('Reduce nonessential motion').isChecked(),false);
 });
 await check('Staff is denied administrator routes after direct navigation',async()=>{await page.goto(base+'/app/admin/users');await page.getByRole('heading',{name:/not available|permission|access|private|Not for/i}).first().waitFor({timeout:3000}).catch(()=>{});assert.match(page.url(),/\/403/);});
 await signIn('Elias Noor Demo');
 await check('Mobile settings and admin tables have no page-wide overflow',async()=>{
  await page.setViewportSize({width:390,height:844});await visit('/app/settings?section=appearance');assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await screenshot('settings-mobile');await visit('/app/admin/users');assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await screenshot('users-mobile');await page.getByRole('button',{name:'Open navigation'}).click();await page.getByRole('button',{name:'Close navigation'}).click({position:{x:365,y:340}});
 });
 await check('Tablet and wide desktop administration render cleanly',async()=>{await page.setViewportSize({width:768,height:1024});await visit('/app/admin/assignments');assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await screenshot('assignments-tablet');await page.setViewportSize({width:1920,height:1080});await visit('/app/admin');await screenshot('overview-wide');});
 await check('No JavaScript errors or failed route resources',async()=>{assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);});
}catch(e){console.error(e);process.exitCode=1;}finally{await fs.writeFile(path.join(output,'results.json'),JSON.stringify({date:new Date().toISOString(),browser:await browser.version(),mode:'Headless Chrome; desktop/tablet/mobile viewport emulation, not real mobile device',checks,errors,requests},null,2));await browser.close();}

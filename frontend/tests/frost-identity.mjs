// REAL local API3/SQLite/private artifacts. Only the fixed provider SDK/verifier is TEST ONLY.
// Does not create separation jobs, execute a model or interact with the owner's browser.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import path from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';
import {canonicalHandle,handleProblem} from '../src/frost/identity.ts';

const base='http://127.0.0.1:4197';
const output=path.resolve(process.env.EVIDENCE_ROOT||'output/playwright/identity-foundation/v1');
await mkdir(output,{recursive:true});
const report={scope:'REAL isolated API3 and SQLite; TEST ONLY fixed fictional identity provider; no API mocks, inference or T9',checks:[],screenshots:[]};
async function api(endpoint,uid='alice',options={}) {const response=await fetch(base+'/api'+endpoint,{...options,headers:{Authorization:'Bearer M1-MOCK:'+uid,...options.headers}});assert.equal(response.status,200,endpoint);return response.json();}
const initialAlice=(await api('/auth/me')).user;
const [records,results]=await Promise.all([api('/recordings'),api('/results')]);
const readyResult=results.items.find(item=>item.provenance?.input_artifact_sha256==='8e0efd28aaf89f7efbd8107805a74bd837bcc70ea3dc4b4b783eff0e6a220616');
assert(readyResult,'Reuse an already completed raw eligible M0001 result; never create another.');
const readyRecord=records.items.find(item=>item.id===readyResult.recording_id);assert(readyRecord?.public_id);
report.owner={handle:initialAlice.handle,publicId:initialAlice.public_id,changeCount:initialAlice.handle_change_count};
assert.equal(initialAlice.handle_change_count,0,'Keep the owner identity change available.');
await api('/auth/session','bob',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
await api('/auth/me','bob',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({display_name:'Local identity reviewer'})});
const bob=(await api('/auth/me','bob')).user;
assert.equal(bob.handle_change_count,0,'Use a fresh fictional browser test actor; do not reset spent changes.');
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true});
const errors=[];
async function context(uid,viewport={width:1440,height:900}) {
  const c=await browser.newContext({viewport});
  c.on('page',p=>p.on('pageerror',error=>errors.push(error.message)));
  await c.route('**/node_modules/.vite/deps/firebase_app.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-app.mjs')}));
  await c.route('**/node_modules/.vite/deps/firebase_auth.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-auth.mjs')}));
  await c.route('**/src/config/runtime.ts*',r=>r.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
  await c.addInitScript(({uid,origin})=>{if(location.origin===origin)sessionStorage.setItem('__m1_test_identity',JSON.stringify({uid,verified:true}));},{uid,origin:base});
  await c.route(url=>['http:','https:'].includes(url.protocol)&&url.origin!==base,r=>r.abort());
  return c;
}
const owner=await context('alice'),page=await owner.newPage();
async function check(name,fn){await fn();report.checks.push({name,status:'PASS'});console.log('PASS',name);}
async function shot(name,p=page){await p.evaluate(()=>document.fonts.ready);await p.screenshot({path:path.join(output,name)});report.screenshots.push(name);}
async function noOverflow(p=page){assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
try{
  await check('client validation matches canonical format; never guesses uniqueness',async()=>{
    assert.equal(canonicalHandle(' Winter.Owl '),'winter.owl');
    for(const invalid of ['ab','2owl','owl_','owl..name','owl_.name','admin','a@example.invalid'])assert(handleProblem(invalid));
    for(const valid of ['winter.owl','owl_27','frostcedar'])assert.equal(handleProblem(valid),'');
  });
  await check('REAL owner profile: actual handle/reference, count0, no preview data; desktop and mobile',async()=>{
    await page.goto(base+'/app/profile');await page.getByRole('heading',{name:'Your profile',exact:true}).waitFor();
    assert.equal(await page.getByRole('textbox',{name:'Handle',exact:true}).inputValue(),initialAlice.handle);
    assert.equal(await page.getByRole('button',{name:'Copy '+initialAlice.public_id,exact:true}).count(),1);
    assert(!await page.locator('.sf-app').innerText().then(text=>/silverdragonfly|Local design preview|Synthetic recordings/.test(text)));
    await noOverflow();await shot('01-profile-frost-desktop.png');
    await page.setViewportSize({width:390,height:844});await noOverflow();await shot('02-profile-frost-mobile.png');
    await page.setViewportSize({width:1024,height:768});await noOverflow();await shot('03-profile-frost-tablet.png');
    await page.setViewportSize({width:1440,height:900});
  });
  await check('REAL appearance and 0–200 device gain; legacy query routes; Midnight and keyboard focus',async()=>{
    await page.goto(base+'/app/settings?section=appearance');await page.getByRole('heading',{name:'Appearance',exact:true}).waitFor();
    await page.getByRole('button',{name:/Midnight A calm/}).click();assert.equal(await page.locator('.sf-app').getAttribute('data-theme'),'midnight');
    await shot('04-appearance-midnight-desktop.png');
    await page.goto(base+'/app/profile');await page.getByRole('heading',{name:'Your profile',exact:true}).waitFor();await shot('05-profile-midnight-desktop.png');
    await page.goto(base+'/app/settings?section=recording');const slider=page.getByRole('slider',{name:'Preferred playback gain',exact:true});await slider.waitFor();
    await slider.focus();await slider.press('Home');for(let i=0;i<30;i++)await slider.press('ArrowRight');
    assert.equal(await slider.inputValue(),'150');assert.match(await slider.getAttribute('aria-valuetext'),/150 percent, boost enabled/);
    await shot('06-audio-midnight-boost.png');await slider.press('End');assert.equal(await slider.inputValue(),'200');
    const ring=await slider.evaluate(el=>({style:getComputedStyle(el).outlineStyle,width:getComputedStyle(el).outlineWidth}));assert.notEqual(ring.style,'none');assert.notEqual(ring.width,'0px');
    await slider.press('Home');for(let i=0;i<20;i++)await slider.press('ArrowRight');
    await page.reload();assert.equal(await page.getByRole('slider',{name:'Preferred playback gain',exact:true}).inputValue(),'100');
    await page.goto(base+'/app/settings?section=data');await page.getByRole('heading',{name:'Your data, under your control',exact:true}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Not available yet',exact:true}).count(),2);
    await page.getByRole('button',{name:'Switch to Frost theme',exact:true}).click();
  });
  await check('REAL Library REC search and unchanged recording/result navigation + authorized audio',async()=>{
    await page.goto(base+'/app/library');await page.locator('.sf-recordings li').first().waitFor();
    const search=page.getByRole('searchbox',{name:'Search recordings by title or public reference'});
    await search.fill(readyRecord.public_id.toLowerCase());assert.equal(await page.locator('.sf-recordings li').count(),1);
    await page.locator('.sf-row-action').click();assert.equal(new URL(page.url()).pathname,'/app/recordings/'+readyRecord.id);
    await page.getByRole('button',{name:'Copy '+readyRecord.public_id,exact:true}).first().waitFor();
    await page.waitForFunction(()=>document.querySelectorAll('.sf-player[data-media-state="ready"]').length===3);
    assert.equal(await page.locator('.sf-comparison-table').count(),1);
    await page.getByRole('link',{name:'StethoFuse Overview',exact:true}).click();assert.equal(new URL(page.url()).pathname,'/app/overview');
    await page.locator('.sf-greeting-handle').waitFor();assert.match(await page.locator('.sf-greeting-handle').innerText(),new RegExp(initialAlice.handle));
    await shot('07-overview-real-public-identity.png');
    await page.goto(base+'/app/library');await page.locator('.sf-recordings li').first().waitFor();await noOverflow();await shot('08-library-real-public-ids.png');
  });
  await check('REAL profile PATCH: collision does not consume change; explicit one-change confirmation; persistence',async()=>{
    const c=await context('bob'),p=await c.newPage();await p.goto(base+'/app/profile');await p.getByRole('heading',{name:'Your profile',exact:true}).waitFor();
    const handle=p.getByRole('textbox',{name:'Handle',exact:true}),name=p.getByRole('textbox',{name:'Display name',exact:true});
    await handle.fill(initialAlice.handle.toUpperCase());await p.getByRole('button',{name:'Save changes',exact:true}).click();
    await p.getByRole('dialog',{name:'Make this handle yours?'}).waitFor();await p.getByRole('button',{name:'Confirm handle change',exact:true}).click();
    await p.getByText('That handle is already in use. Try another name.',{exact:true}).waitFor();assert.equal((await api('/auth/me','bob')).user.handle_change_count,0);
    const renamed='review.owl27';await handle.fill('Review.Owl27');await name.fill('Local identity reviewer');
    await p.getByRole('button',{name:'Save changes',exact:true}).click();await p.getByRole('dialog',{name:'Make this handle yours?'}).waitFor();
    await shot('09-one-change-confirmation.png',p);await p.getByRole('button',{name:'Confirm handle change',exact:true}).click();
    await p.getByText('Profile saved.',{exact:true}).waitFor();assert.equal(await handle.inputValue(),renamed);assert(await handle.evaluate(el=>el.readOnly));
    await p.reload();await p.getByRole('heading',{name:'Your profile',exact:true}).waitFor();assert.equal(await p.getByRole('textbox',{name:'Handle',exact:true}).inputValue(),renamed);
    await p.getByRole('textbox',{name:'Display name',exact:true}).fill('Local reviewer — name remains editable');await p.getByRole('button',{name:'Save changes',exact:true}).click();await p.getByText('Profile saved.',{exact:true}).waitFor();
    await shot('10-one-change-used-profile.png',p);const saved=(await api('/auth/me','bob')).user;
    assert.equal(saved.public_id,bob.public_id);assert.equal(saved.id,bob.id);assert.equal(saved.uid,bob.uid);assert.equal(saved.handle_change_count,1);
    report.testActor={uid:'bob',publicId:saved.public_id,handle:saved.handle,changeCount:saved.handle_change_count};await c.close();
    const fresh=await context('bob'),freshPage=await fresh.newPage();await freshPage.goto(base+'/app/profile');await freshPage.getByRole('heading',{name:'Your profile',exact:true}).waitFor();assert.equal(await freshPage.getByRole('textbox',{name:'Handle',exact:true}).inputValue(),renamed);await fresh.close();
  });
  await check('REAL owner remains unchanged; local motion/overflow and no browser exceptions',async()=>{
    assert.deepEqual((await api('/auth/me')).user,initialAlice);
    await page.emulateMedia({reducedMotion:'reduce'});await page.goto(base+'/app/profile');await page.getByRole('heading',{name:'Your profile',exact:true}).waitFor();
    const control=page.getByRole('button',{name:'Save changes',exact:true});assert.equal(await control.evaluate(el=>getComputedStyle(el).transitionDuration),'0s');
    await noOverflow();assert.deepEqual(errors,[]);
  });
  report.status='PASS';report.consoleErrors=errors;
}catch(error){report.status='FAIL';report.error=error.message;throw error;}
finally{await writeFile(path.join(output,'receipt.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}

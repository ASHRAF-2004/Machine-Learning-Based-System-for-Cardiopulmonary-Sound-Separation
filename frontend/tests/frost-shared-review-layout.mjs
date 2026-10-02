// Read-only final capture of the prepared manual assignments; no grant/profile/notes edits.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import path from 'node:path';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
const origin='http://127.0.0.1:4199',out=path.resolve('output/playwright/shared-reviews/final-layout-v2');
await mkdir(out,{recursive:true});
const manual=JSON.parse(await readFile('../.local/shared-review/manual-assignments.json','utf8'));
const original=manual.items.find(item=>item.scope==='Original audio only'),result=manual.items.find(item=>item.scope==='Result details only');
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true}),c=await browser.newContext({viewport:{width:1440,height:900}}),errors=[];
await c.route('**/node_modules/.vite/deps/firebase_app.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-app.mjs')}));
await c.route('**/node_modules/.vite/deps/firebase_auth.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-auth.mjs')}));
await c.route('**/src/config/runtime.ts*',r=>r.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
await c.addInitScript(origin=>{if(location.origin===origin)sessionStorage.setItem('__m1_test_identity',JSON.stringify({uid:'analyst',verified:true}));},origin);
await c.route(value=>['http:','https:'].includes(value.protocol)&&value.origin!==origin,r=>r.abort());
const p=await c.newPage();p.on('pageerror',e=>errors.push(e.message));const report={screenshots:[]};
async function shot(name){await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(250);assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.screenshot({path:path.join(out,name)});report.screenshots.push(name);}
try{
  await p.goto(origin+'/app/shared');await p.getByRole('button',{name:'Assigned reviews',exact:true}).waitFor();await p.getByRole('link',{name:'Open nm',exact:true}).waitFor();await shot('01-shared-desktop.png');
  await p.getByRole('button',{name:'Assigned reviews',exact:true}).click();await p.getByRole('list',{name:'Assigned reviews',exact:true}).waitFor();assert.equal(await p.locator('.sf-assignment-list li').count(),2);await shot('02-assigned-desktop.png');
  await p.goto(origin+'/app/reviews/'+original.assignmentId);await p.locator('.sf-player[data-media-state="ready"]').waitFor();await shot('03-original-review-desktop.png');
  const editor=p.getByRole('region',{name:'Your review',exact:true});await editor.scrollIntoViewIfNeeded();await p.waitForTimeout(250);const bounds=await editor.boundingBox();if(bounds.y<88)await p.mouse.wheel(0,bounds.y-88);await shot('04-review-notes-desktop.png');
  report.notesFont=await p.getByRole('textbox',{name:'Review notes',exact:true}).evaluate(el=>getComputedStyle(el).fontSize);
  assert(parseFloat(report.notesFont)>=14,'Review notes retain readable operational type');
  await p.setViewportSize({width:390,height:844});await p.goto(origin+'/app/shared?view=assigned');await p.getByRole('list',{name:'Assigned reviews',exact:true}).waitFor();await shot('05-assigned-mobile.png');
  await p.goto(origin+'/app/reviews/'+original.assignmentId);await p.locator('.sf-player[data-media-state="ready"]').waitFor();await editor.scrollIntoViewIfNeeded();await p.waitForTimeout(250);await shot('06-review-notes-mobile.png');
  await p.setViewportSize({width:820,height:1000});await p.goto(origin+'/app/shared?view=assigned');await p.getByRole('list',{name:'Assigned reviews',exact:true}).waitFor();await shot('07-assigned-tablet.png');
  await p.setViewportSize({width:1440,height:900});await p.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await shot('08-assigned-midnight.png');
  await p.goto(origin+'/app/reviews/'+result.assignmentId);await p.getByRole('textbox',{name:'Review notes',exact:true}).waitFor();assert.equal(await p.locator('.sf-player').count(),0);await shot('09-result-only-review.png');
  assert.deepEqual(errors,[]);report.status='PASS';console.log('PASS: real shared/assigned/manual review desktop/mobile/tablet/Midnight captures; no horizontal overflow/JS exceptions; result-only still has no output audio; notes font '+report.notesFont);
}catch(error){report.status='FAIL';report.error=error.message;throw error;}
finally{await writeFile(path.join(out,'receipt.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}

// Read-only final compact/history visual follow-up. No grants or profile edits.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import path from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';
const origin='http://127.0.0.1:4198',out=path.resolve('output/playwright/handle-sharing/final-layout-v2');await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true});
const report={scope:'Read-only real local API, fixed test SDK; no grants, identity changes or inference.',checks:[],screenshots:[]};
try{
  const c=await browser.newContext({viewport:{width:1440,height:900}});
  await c.route('**/node_modules/.vite/deps/firebase_app.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-app.mjs')}));
  await c.route('**/node_modules/.vite/deps/firebase_auth.js*',r=>r.fulfill({contentType:'application/javascript',path:path.resolve('tests/m1/mock-firebase-auth.mjs')}));
  await c.route('**/src/config/runtime.ts*',r=>r.fulfill({contentType:'application/javascript',body:"export const FIREBASE_PROJECT='stethofuse-c18cd-3cca0';export const PUBLIC_ORIGIN='https://stethofuse.ashraf-alsaloul.com';export const DEMO_ENABLED=false;export const firebaseConfigurationError='';export const firebaseConfiguration=()=>({projectId:FIREBASE_PROJECT});"}));
  await c.addInitScript(()=>sessionStorage.setItem('__m1_test_identity',JSON.stringify({uid:'alice',verified:true})));
  await c.route(url=>['http:','https:'].includes(url.protocol)&&url.origin!==origin,r=>r.abort());
  const p=await c.newPage(),errors=[];p.on('pageerror',error=>errors.push(error.message));
  await p.goto(origin+'/app/recordings/e45bc435dcdd417dbfde109a44f11274');await p.waitForFunction(()=>document.querySelectorAll('.sf-player[data-media-state="ready"]').length===3);
  await p.getByRole('button',{name:'Share',exact:true}).click();const sharing=p.getByRole('region',{name:'Recording sharing'});
  await sharing.getByText('No one else has access. Your recording is private.',{exact:true}).waitFor();assert.equal(await sharing.locator('.sf-grant-list li').count(),0);
  const more=sharing.getByRole('button',{name:/^See more/});await more.focus();await p.keyboard.press('Enter');await sharing.locator('.sf-grant-list li').first().waitFor();assert(await sharing.locator('.sf-grant-list li').count()>3);
  await sharing.getByRole('button',{name:'See less',exact:true}).focus();await p.keyboard.press('Space');assert.equal(await sharing.locator('.sf-grant-list li').count(),0);
  assert(await sharing.getByRole('button',{name:/^See more/}).evaluate(el=>el===document.activeElement));
  report.checks.push('PASS: no active permissions means a truthful private state; revoked history only appears under See more; keyboard collapse retains focus');
  async function shot(name,target){
    await target.scrollIntoViewIfNeeded();
    // Frame below the sticky header using normal scrolling, not DOM/style edits.
    await p.waitForTimeout(250);const box=await target.boundingBox();
    if(box&&box.y<88)await p.mouse.wheel(0,box.y-96);
    await p.waitForTimeout(250);assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await p.screenshot({path:path.join(out,name)});report.screenshots.push(name);
  }
  await shot('01-sharing-private-desktop.png',sharing);
  const details=p.locator('.sf-core-technical');await details.locator('summary').click();await shot('02-details-desktop.png',details);
  await p.setViewportSize({width:390,height:844});await shot('03-details-mobile.png',details);await shot('04-sharing-mobile.png',sharing);
  await p.setViewportSize({width:820,height:1000});await shot('05-details-tablet.png',details);
  await p.setViewportSize({width:1440,height:900});await p.getByRole('button',{name:'Switch to Midnight theme',exact:true}).click();await shot('06-details-midnight.png',details);await shot('07-sharing-midnight.png',sharing);
  assert.deepEqual(errors,[]);report.checks.push('PASS: final desktop/mobile/tablet/Frost/Midnight screenshots, no horizontal overflow or page errors');report.status='PASS';console.log(report.checks.join('\n'));
}catch(error){report.status='FAIL';report.error=error.message;throw error;}
finally{await writeFile(path.join(out,'receipt.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}

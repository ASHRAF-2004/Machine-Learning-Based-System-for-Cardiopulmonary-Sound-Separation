import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const output=path.join(root,process.env.EVIDENCE_ROOT || 'evidence','analyst-responsive');
const base=process.env.FRONTEND_URL||'http://127.0.0.1:4180';
await mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const results=[],errors=[],contrast=[],scrolling=[];
async function check(name,fn){try{await fn();results.push({name,status:'PASS'});console.log('PASS '+name);}catch(e){results.push({name,status:'FAIL',error:e.message});console.error('FAIL '+name+': '+e.message);}}
async function settle(page){await page.locator('h1').first().waitFor();await page.evaluate(()=>document.fonts.ready);await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));}
async function overflow(page){return page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth}));}
async function measureText(page,label,selectors){
 const data=await page.evaluate(selectors=>{
  const parse=c=>{const a=c.match(/[\d.]+/g)?.map(Number)||[0,0,0];return [a[0],a[1],a[2],a[3]??1];};
  const blend=(front,back)=>[0,1,2].map(i=>front[i]*front[3]+back[i]*(1-front[3]));
  const luminance=rgb=>{const a=rgb.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;});return a[0]*.2126+a[1]*.7152+a[2]*.0722;};
  return selectors.flatMap(selector=>{
   const element=document.querySelector(selector);if(!element)return [];
   const css=getComputedStyle(element),parents=[];let node=element;
   while(node){parents.unshift(node);node=node.parentElement;}
   let background=[255,255,255],image=false,opacity=false;
   for(const parent of parents){const style=getComputedStyle(parent);background=blend(parse(style.backgroundColor),background);image||=style.backgroundImage!=='none';opacity||=Number(style.opacity)!==1;}
   const fg=blend(parse(css.color),background),a=luminance(fg),b=luminance(background),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
   const fontSize=parseFloat(css.fontSize),fontWeight=Number(css.fontWeight),threshold=fontSize>=24||(fontSize>=18.6667&&fontWeight>=700)?3:4.5;
   return [{selector,text:element.textContent.trim().slice(0,90),foreground:css.color,backgroundRGB:background.map(v=>+v.toFixed(2)),fontSize,fontWeight,ratio:+ratio.toFixed(4),threshold,result:image||opacity?'NOT VERIFIED: image/opacity context':ratio>=threshold?'PASS':'FAIL',hasBackgroundImage:image,hasAncestorOpacity:opacity}];
  });
 },selectors);
 contrast.push({page:label,measurements:data});
}
try{
 for(const width of [390,768]){
  const context=await browser.newContext({viewport:{width,height:width===390?844:1024},reducedMotion:'reduce'}),page=await context.newPage();
  page.on('pageerror',e=>errors.push({width,message:e.message}));
  await page.goto(base+'/login',{waitUntil:'networkidle'});
  // Isolated, fictional fixture bootstrap, not a production login bypass.
  await page.evaluate(()=>sessionStorage.setItem('stethofuse-demo-persona','USR-2001'));
  await page.goto(base+'/app/reviews/ASN-401',{waitUntil:'networkidle'});await settle(page);
  await check(`${width}px analyst review has no whole-page horizontal overflow`,async()=>{const o=await overflow(page);assert.ok(o.document<=o.viewport&&o.body<=o.viewport,JSON.stringify(o));});
  await check(`${width}px note controls are keyboard reachable and save a timestamp`,async()=>{
   const time=page.getByLabel('Time in seconds',{exact:true}),note=page.getByLabel('Observation',{exact:true});
   await time.fill('0.7');await page.keyboard.press('Tab');assert.equal(await note.evaluate(e=>document.activeElement===e),true);
   await note.fill(`Responsive ${width}px check: brief synthetic amplitude change.`);await page.keyboard.press('Tab');
   assert.equal(await page.getByRole('button',{name:'Add note',exact:true}).evaluate(e=>document.activeElement===e),true);
   await page.keyboard.press('Enter');await page.getByText(`Responsive ${width}px check: brief synthetic amplitude change.`,{exact:true}).waitFor();
  });
  await check(`${width}px review draft persists across refresh`,async()=>{
   await page.getByLabel('Review summary').fill(`Fictional ${width}px responsive review. No clinical interpretation.`);
   await page.getByRole('button',{name:'Save draft',exact:true}).click();
   await page.reload({waitUntil:'networkidle'});await settle(page);
   assert.equal(await page.getByLabel('Review summary').inputValue(),`Fictional ${width}px responsive review. No clinical interpretation.`);
   assert.ok(await page.getByText(`Responsive ${width}px check: brief synthetic amplitude change.`,{exact:true}).count());
  });
  const notes=page.locator('section.panel').filter({has:page.getByRole('heading',{name:'Timestamped observations',exact:true})});
  const decision=page.locator('section.panel').filter({has:page.getByRole('heading',{name:'Review decision',exact:true})});
  await page.screenshot({path:path.join(output,`review-${width}.png`),fullPage:true});
  await notes.screenshot({path:path.join(output,`notes-${width}.png`)});
  await decision.screenshot({path:path.join(output,`decision-${width}.png`)});
  if(width===390)await measureText(page,'analyst review default palette',['h1','.eyebrow','.breadcrumbs','.demo-banner','.panel-heading p','.field>span','.field>small','.note-text','.timestamp-note code','.timestamp-note p','.workspace-footer','.badge-warning','.button-primary']);
  await check(`${width}px decision control, confirmation and submission are usable`,async()=>{
   const value=width===390?'reviewed':'re-record';await page.getByLabel('Decision',{exact:true}).selectOption(value);
   await page.getByRole('button',{name:'Submit review',exact:true}).click();
   const dialog=page.getByRole('dialog').filter({has:page.getByRole('button',{name:'Submit decision',exact:true})});
   await dialog.waitFor();const box=await dialog.boundingBox();assert.ok(box.x>=0&&box.x+box.width<=width+1);
   await page.screenshot({path:path.join(output,`confirmation-${width}.png`)});
   await page.getByRole('button',{name:'Submit decision',exact:true}).click();await dialog.waitFor({state:'hidden'});
   const stored=await page.evaluate(()=>JSON.parse(localStorage.getItem('stethofuse-demo-v1')).reviews.find(r=>r.assignmentId==='ASN-401'));
   assert.equal(stored.decision,value);assert.equal(stored.notes.length,1);
  });
  await check(`${width}px waveform/spectrogram tabs switch without overflow`,async()=>{
   await page.getByRole('tab',{name:'Spectrograms',exact:true}).click();assert.equal(await page.locator('canvas').count(),3);
   await page.getByRole('tab',{name:'Waveforms',exact:true}).click();const o=await overflow(page);assert.ok(o.document<=width);
  });
  await page.goto(base+'/app/assigned',{waitUntil:'networkidle'});await settle(page);
  const tables=await page.locator('.table-scroll').evaluateAll(elements=>elements.map(e=>({clientWidth:e.clientWidth,scrollWidth:e.scrollWidth,overflowX:getComputedStyle(e).overflowX,tabIndex:e.tabIndex,role:e.getAttribute('role'),ariaLabel:e.getAttribute('aria-label'),nearbyText:e.parentElement.innerText.slice(0,450)})));
  const tabScroll=await page.locator('.tabs').evaluateAll(elements=>elements.map(e=>({clientWidth:e.clientWidth,scrollWidth:e.scrollWidth,overflowX:getComputedStyle(e).overflowX})));
  scrolling.push({width,tables,tabs:tabScroll});
  await page.screenshot({path:path.join(output,`assigned-${width}.png`),fullPage:true});
  await check(`${width}px assigned list horizontal scrolling is local to table`,async()=>{
   const o=await overflow(page);assert.ok(o.document<=width);
   for(const table of await page.locator('.table-scroll').all()){if(await table.evaluate(e=>e.scrollWidth>e.clientWidth)){await table.evaluate(e=>e.scrollLeft=e.scrollWidth);assert.ok(await table.evaluate(e=>e.scrollLeft>0));}}
  });
  await context.close();
 }
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'}),page=await context.newPage();
 await page.goto(base+'/login',{waitUntil:'networkidle'});await settle(page);
 await measureText(page,'public login default palette',['.auth-form h1','.auth-form>.muted','.auth-demo-note','.auth-form .field>span','.auth-form .field small','.auth-links','.auth-meta','.form-divider','.auth-foot','.button-primary']);
 await page.goto(base+'/register',{waitUntil:'networkidle'});await settle(page);
 await measureText(page,'public registration default palette',['.auth-consent','.auth-account-scope','.auth-form .field small','.auth-state-picker>summary']);
 await context.close();
 await check('No browser runtime errors in responsive analyst checks',async()=>assert.deepEqual(errors,[]));
 const report={generatedAt:new Date().toISOString(),browser:await browser.version(),base,method:'Headless Chrome, separate contexts, 390×844 and 768×1024 viewport emulation, reduced motion; synthetic fixtures, not physical devices or live authorization',results,errors,scrolling,contrast,contrastMethod:'WCAG relative luminance (sRGB linearization) of computed text over composed solid ancestor backgrounds; 4.5:1 normal text, 3:1 large text. Excludes background-image/opacity contexts from PASS claims; does not test all content, placeholder text, focus or UI non-text contrast.',pass:results.filter(r=>r.status==='PASS').length,fail:results.filter(r=>r.status==='FAIL').length};
 await writeFile(path.join(output,'results.json'),JSON.stringify(report,null,2));
 console.log('CONTRAST FAILURES',JSON.stringify(contrast.flatMap(group=>group.measurements.filter(m=>m.result==='FAIL').map(m=>({page:group.page,...m}))),null,2));
 process.exitCode=report.fail?1:0;
}finally{await browser.close();}

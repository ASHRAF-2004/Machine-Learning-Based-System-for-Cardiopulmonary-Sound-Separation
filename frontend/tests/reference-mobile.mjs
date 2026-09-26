import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';

const base=process.env.FRONTEND_URL||'http://127.0.0.1:4180';
const output=path.resolve(process.env.EVIDENCE_ROOT||'evidence/reference-match/functional','mobile');
await mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const checks=[];
try{
 for(const entry of [
  {name:'dashboard',persona:'USR-1001',route:'/app/dashboard'},
  {name:'admin-users',persona:'USR-3001',route:'/app/admin/users'},
  {name:'settings',persona:'USR-1001',route:'/app/settings'},
  {name:'settings-appearance',persona:'USR-1001',route:'/app/settings?section=appearance'},
  {name:'shared',persona:'USR-1001',route:'/app/shared'},
  {name:'403',persona:'USR-1001',route:'/403'},
 ]){
  const context=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1});
  const page=await context.newPage(),errors=[],failedResponses=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('response',response=>{if(response.status()>=400)failedResponses.push({url:response.url(),status:response.status()});});
  const result={...entry,status:'PASS',errors,failedResponses};
  try{
   await page.goto(base);
   await page.evaluate(persona=>sessionStorage.setItem('stethofuse-demo-persona',persona),entry.persona);
   await page.goto(base+entry.route);
   await page.locator('main h1').waitFor();
   await page.evaluate(()=>document.fonts.ready);
   await page.reload();
   await page.locator('main h1').waitFor();
   await page.evaluate(()=>document.fonts.ready);
   result.layout=await page.evaluate(()=>({
    viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,
    heading:document.querySelector('main h1')?.textContent,
    scrollContainers:[...document.querySelectorAll('main *')].filter(element=>element.scrollWidth>element.clientWidth+1&&['auto','scroll'].includes(getComputedStyle(element).overflowX)).map(element=>({tag:element.tagName,className:element.className,clientWidth:element.clientWidth,scrollWidth:element.scrollWidth})),
    outsideViewport:[...document.querySelectorAll('main *')].filter(element=>{const rect=element.getBoundingClientRect();return rect.width>0&&(rect.left<-.5||rect.right>innerWidth+.5);}).slice(0,40).map(element=>({tag:element.tagName,className:element.className,text:element.textContent?.slice(0,90),left:element.getBoundingClientRect().left,right:element.getBoundingClientRect().right})),
    brokenImages:[...document.querySelectorAll('img')].filter(image=>image.complete&&image.naturalWidth===0).map(image=>image.currentSrc||image.src),
   }));
   assert(result.layout.documentWidth<=391,`Page overflow: ${result.layout.documentWidth}px at 390px`);
   assert.deepEqual(errors,[]);
   assert.deepEqual(failedResponses,[]);
   assert.deepEqual(result.layout.brokenImages,[]);
  }catch(error){result.status='FAIL';result.error=error.message;process.exitCode=1;}
  await page.screenshot({path:path.join(output,`${entry.name}-390.png`),fullPage:true});
  checks.push(result);console.log(`${result.status} ${entry.name}: ${result.error||`${result.layout.documentWidth}px document at 390px`}`);
  await context.close();
 }
}finally{
 await writeFile(path.join(output,'results.json'),JSON.stringify({testedAt:new Date().toISOString(),browser:await browser.version(),scope:'390px isolated-context mobile containment after refresh; internal scroll containers reported separately',checks},null,2));
 await browser.close();
}

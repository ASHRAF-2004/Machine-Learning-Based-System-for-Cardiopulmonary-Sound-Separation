import {chromium} from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';
const out=path.resolve('evidence/reference-match/visual');
await fs.mkdir(out,{recursive:true});
const base=process.env.STETHOFUSE_TEST_URL||'http://127.0.0.1:4180';
const cases=[
 ['dashboard','USR-3001','/app/dashboard'],
 ['recordings','USR-1001','/app/recordings'],
 ['recordings-empty','USR-3001','/app/recordings'],
 ['results','USR-1001','/app/results'],
 ['processing','USR-1001','/app/processing'],
 ['history','USR-1001','/app/history'],
 ['shared','USR-1001','/app/shared'],
 ['recording-detail','USR-1002','/app/recordings/REC-1047'],
 ['review-queue','USR-2001','/app/review-queue'],
 ['assigned','USR-2001','/app/assigned'],
 ['settings','USR-1001','/app/settings'],
 ['appearance','USR-1001','/app/settings?section=appearance'],
 ['ensemble','USR-3001','/app/admin/ensemble'],
 ['audit','USR-3001','/app/admin/audit'],
 ['system','USR-3001','/app/admin/settings'],
 ['403','USR-1001','/403'],
];
const filter=process.env.CASES?.split(',');
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const results=[],errors=[];
try{
 for(const [name,persona,route] of cases.filter(c=>!filter||filter.includes(c[0]))){
  const context=await browser.newContext({viewport:{width:1586,height:992},deviceScaleFactor:1,reducedMotion:'reduce'});
  await context.addInitScript(id=>sessionStorage.setItem('stethofuse-demo-persona',id),persona);
  const page=await context.newPage();
  page.on('pageerror',e=>errors.push({name,message:e.message}));
  page.on('response',r=>{if(r.status()>=400)errors.push({name,status:r.status(),url:r.url()});});
  const start=Date.now();
  await page.goto(base+route);
  await page.locator('h1').first().waitFor();
  await page.evaluate(()=>document.fonts.ready);
  await page.waitForLoadState('networkidle');
  await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});
  const data=await page.evaluate(()=>{
   const bounds=selector=>[...document.querySelectorAll(selector)].map(el=>{const b=el.getBoundingClientRect();return {selector,x:b.x,y:b.y,w:b.width,h:b.height};});
   return {viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},height:document.documentElement.scrollHeight,overflow:document.documentElement.scrollWidth>innerWidth+1,title:document.querySelector('h1')?.textContent,
    bounds:['.page-heading','.workspace-overview','.workspace-counts','.workspace-dashboard-grid','.settings-layout','.filter-bar','.table-scroll','.utility-inner'].flatMap(bounds),
    resources:performance.getEntriesByType('resource').filter(x=>x.name.includes('/assets/')).map(x=>({url:x.name.split('/assets/')[1],transfer:x.transferSize,encoded:x.encodedBodySize,decoded:x.decodedBodySize}))};
  });
  results.push({name,route,...data,observedLoadAndIdleMs:Date.now()-start});
  console.log(`${name}: ${data.height}px high; overflow=${data.overflow}`);
  await context.close();
 }
}finally{await fs.writeFile(path.join(out,'metrics.json'),JSON.stringify({browser:await browser.version(),environment:'Local Chrome desktop automation,1586×992,DPR1,reduced motion; no physical-device claims. Load interval includes network-idle settling, not LCP.',results,errors},null,2));await browser.close();}
if(errors.length||results.some(r=>r.overflow))process.exitCode=1;

import {chromium} from 'playwright-core';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';

const root=path.resolve(import.meta.dirname,'..');
const output=path.join(root,'evidence/winter-glass/visual-workspace');
const base=process.env.STETHOFUSE_TEST_URL||process.env.FRONTEND_URL||'http://127.0.0.1:4180';
await mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const pages=[],errors=[],failedResources=[];
async function capture(page,name,route){
  if(route)await page.goto(new URL(route,base).href);
  await page.locator('h1').first().waitFor();
  await page.evaluate(()=>document.fonts.ready);
  await page.waitForTimeout(250);
  const details=await page.evaluate(()=>({
    route:location.pathname,heading:document.querySelector('h1')?.textContent,
    viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,
    tables:[...document.querySelectorAll('.table-scroll')].map(el=>({clientWidth:el.clientWidth,scrollWidth:el.scrollWidth,overflowX:getComputedStyle(el).overflowX})),
    layout:[...document.querySelectorAll('.workspace,.workspace-dashboard-grid,.workspace-overview,.workspace-counts,.capture-layout,.recording-detail-layout,.processing-detail-layout,.review-layout,.note-entry,.audio-workbench')].map(el=>{
      const r=el.getBoundingClientRect();return {selector:'.'+[...el.classList].join('.'),x:r.x,width:r.width,right:r.right};
    }),
    textStyles:['.page-description','.panel-heading p','.note-text','.field small','.level-label','.workspace-footer'].flatMap(selector=>{
      const el=document.querySelector(selector);if(!el)return [];
      const style=getComputedStyle(el);return [{selector,color:style.color,fontSize:style.fontSize}];
    })
  }));
  await page.screenshot({path:path.join(output,name+'.png'),fullPage:true});
  pages.push({name,...details});
  console.log(`${details.documentWidth<=details.viewport+1?'PASS':'FAIL'} document width: ${name} (${details.documentWidth}/${details.viewport})`);
}
async function isolated(persona,width=1440){
  const context=await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:1,reducedMotion:'reduce'});
  await context.addInitScript(id=>sessionStorage.setItem('stethofuse-demo-persona',id),persona);
  const page=await context.newPage();
  page.on('pageerror',error=>errors.push({persona,width,message:error.message}));
  page.on('response',response=>{if(response.status()>=400)failedResources.push({persona,url:response.url(),status:response.status()});});
  return {context,page};
}
try {
  const staff=await isolated('USR-1001');
  await capture(staff.page,'upload-1440','/app/recordings/new/upload');
  await capture(staff.page,'device-idle-1440','/app/recordings/new/record');
  await staff.page.getByRole('button',{name:'Connect demo input',exact:true}).click();
  await capture(staff.page,'device-ready-1440');
  await capture(staff.page,'recording-detail-1440','/app/recordings/REC-1042');
  await capture(staff.page,'processing-detail-1440','/app/processing/JOB-2100');
  await capture(staff.page,'result-detail-1440','/app/results/RES-3100');
  await staff.page.getByRole('tab',{name:'Run provenance',exact:true}).click();
  await capture(staff.page,'result-provenance-1440');
  await capture(staff.page,'shared-1440','/app/shared');
  await staff.context.close();
  const analyst=await isolated('USR-2001');
  await capture(analyst.page,'analyst-queue-1440','/app/review-queue');
  await capture(analyst.page,'analyst-review-1440','/app/reviews/ASN-401');
  await analyst.context.close();
  const staffB=await isolated('USR-1002');
  await capture(staffB.page,'staff-b-dashboard-1440','/app/dashboard');
  await staffB.context.close();
  const admin=await isolated('USR-3001');
  await capture(admin.page,'empty-admin-dashboard-1440','/app/dashboard');
  await admin.context.close();
  const mobile=await isolated('USR-1001',360);
  await capture(mobile.page,'recording-detail-360','/app/recordings/REC-1042');
  await mobile.context.close();
} finally {
  await writeFile(path.join(output,'automated-layout.json'),JSON.stringify({generatedAt:new Date().toISOString(),base,browser:await browser.version(),method:'Isolated fictional contexts; reduced-motion viewport emulation; read-only navigation with a local simulator connection to reveal its ready state. No recordings, reviews or settings saved.',scope:'Document-width and runtime checks only. Screenshot inspection is separate; computed color samples are not a WCAG contrast audit.',pages,errors,failedResources},null,2));
  await browser.close();
}
if(errors.length||failedResources.length||pages.some(page=>page.documentWidth>page.viewport+1))process.exitCode=1;

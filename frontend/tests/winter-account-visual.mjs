import {chromium} from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';

const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'evidence/winter-glass/visual-account');
const base=process.env.STETHOFUSE_TEST_URL||'http://127.0.0.1:4180';
await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const observations=[],errors=[];
const inventories={
 admin:[['ensemble','/app/admin/ensemble'],['audit','/app/admin/audit'],['system-settings','/app/admin/settings'],['users','/app/admin/users'],['user-detail','/app/admin/users/USR-1001']],
 staff:[['profile','/app/profile'],['notifications','/app/notifications'],['help','/app/help'],...['general','appearance','notifications','security','recording','data'].map(section=>[`settings-${section}`,`/app/settings?section=${section}`])],
};

async function capture(page,name,route,width=1440,height=1000){
 await page.setViewportSize({width,height});
 await page.goto(new URL(route,base).href);
 await page.locator('.workspace h1').waitFor({timeout:15000});
 await page.evaluate(()=>document.fonts.ready);
 await page.waitForTimeout(180);
 const metrics=await page.evaluate(()=>{
  const selector=el=>{const parts=[];let node=el;while(node&&node!==document.body&&parts.length<4){let part=node.tagName.toLowerCase();if(node.id){parts.unshift(`#${node.id}`);break;}if(node.classList.length)part+='.'+[...node.classList].slice(0,3).join('.');const same=node.parentElement?[...node.parentElement.children].filter(n=>n.tagName===node.tagName):[];if(same.length>1)part+=`:nth-of-type(${same.indexOf(node)+1})`;parts.unshift(part);node=node.parentElement;}return parts.join(' > ');};
  const visible=el=>{const rect=el.getBoundingClientRect(),style=getComputedStyle(el);return rect.width>0&&rect.height>0&&style.visibility!=='hidden'&&style.display!=='none';};
  const main=document.querySelector('.workspace');
  const controls=[...main.querySelectorAll('button,input:not([type=checkbox]),select,textarea')].filter(visible);
  const clippedControls=controls.filter(el=>el.scrollWidth>el.clientWidth+2&&getComputedStyle(el).overflowX==='hidden').map(el=>({selector:selector(el),text:el.textContent?.trim().slice(0,90),scrollWidth:el.scrollWidth,clientWidth:el.clientWidth}));
  const scrollers=[...main.querySelectorAll('.table-scroll,.settings-nav,.tabs')].map(el=>({selector:selector(el),width:el.clientWidth,scrollWidth:el.scrollWidth,overflowX:getComputedStyle(el).overflowX}));
  const oversized=[...main.querySelectorAll('.panel,.settings-layout,.filter-bar,.help-grid,.notification-list,.page-heading')].filter(el=>{const rect=el.getBoundingClientRect();return rect.left<-.5||rect.right>innerWidth+.5;}).map(el=>({selector:selector(el),left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right}));
  const overlaps=[];
  for(let i=0;i<controls.length;i++)for(let j=i+1;j<controls.length;j++){
   if(controls[i].contains(controls[j])||controls[j].contains(controls[i]))continue;
   const a=controls[i].getBoundingClientRect(),b=controls[j].getBoundingClientRect();
   if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>2&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>2)overlaps.push([selector(controls[i]),selector(controls[j])]);
  }
  const styleSamples=['.page-description','.field small','.setting-row p','.expert-row p','.account-integration-list p','.notification-item p','.note-text'].flatMap(query=>{const el=main.querySelector(query);return el?[{selector:query,color:getComputedStyle(el).color,fontSize:getComputedStyle(el).fontSize,lineHeight:getComputedStyle(el).lineHeight}]:[];});
  return {title:main.querySelector('h1')?.textContent,pageWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,pageHeight:document.documentElement.scrollHeight,overflow:document.documentElement.scrollWidth>innerWidth+1,oversized,clippedControls,overlaps,scrollers,styleSamples,visibleControls:controls.length};
 });
 const screenshot=`${name}-${width}.png`;
 await page.screenshot({path:path.join(out,screenshot),fullPage:true});
 observations.push({name,route,url:page.url(),screenshot,metrics});
 console.log(`${name} ${width}px: overflow=${metrics.overflow}; control overlaps=${metrics.overlaps.length}; oversized surfaces=${metrics.oversized.length}`);
}

try{
 for(const [role,routes] of Object.entries(inventories)){
  const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1,reducedMotion:'reduce'});
  await context.addInitScript(id=>sessionStorage.setItem('stethofuse-demo-persona',id),role==='admin'?'USR-3001':'USR-1001');
  const page=await context.newPage();
  page.on('pageerror',e=>errors.push({role,error:e.message}));
  page.on('response',r=>{if(r.status()>=400)errors.push({role,error:`${r.status()} ${r.url()}`});});
  for(const [name,route] of routes)await capture(page,name,route);
  if(role==='admin')await capture(page,'users-mobile','/app/admin/users',390,844);
  else await capture(page,'settings-mobile','/app/settings?section=general',390,844);
  await context.close();
 }
}finally{
 await fs.writeFile(path.join(out,'metrics.json'),JSON.stringify({scope:'Read-only visual capture using fresh fictional browser contexts. No save, role change, sharing or application mutation actions. Geometry measurements do not certify color contrast or visual appearance.',testedAt:new Date().toISOString(),base,browser:await browser.version(),observations,errors},null,2));
 await browser.close();
}
if(errors.length||observations.some(o=>o.metrics.overflow||o.metrics.oversized.length||o.metrics.overlaps.length))process.exitCode=1;

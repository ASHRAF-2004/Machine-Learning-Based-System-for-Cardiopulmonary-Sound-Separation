// Focused visual diagnosis: actual pointer input and the live WebGL surface.
import {chromium} from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'evidence/owl-smooth-v2',process.env.OWL_EVIDENCE||'diagonal-before');
await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--enable-gpu','--use-gl=angle','--use-angle=gl']});
const page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:2});
const records=[];
const poses=[[0,0],[7.5,4.5],[12,7.2],[17.5,10.5],[21,12.6],[24,10],[-7.5,-4.5],[-12,-7.2],[-17.5,-10.5],[-21,-12.6],[-24,-10]];
for(const layer of (process.env.OWL_LAYERS==='1'?['all','0','1','2']:['all'])){
 await page.goto('http://127.0.0.1:4180/?owlDebug=1'+(process.env.OWL_CANDIDATE==='1'?'&owlCandidate=1':'')+(layer==='all'?'':`&owlLayer=${layer}`));
 await page.waitForFunction(()=>document.querySelector('.owl-art')?.dataset.renderer==='continuous-surface');
 const owl=page.locator('.winter-hero .owl-art');
 const b=await owl.boundingBox(),h=await page.locator('.winter-hero').boundingBox();
 for(const [i,[yaw,pitch]] of poses.entries()){
  await page.mouse.move(b.x+b.width*497.5/1163+yaw/30*Math.max(155,h.width*.34),b.y+b.height*260/1353-pitch/18*Math.max(115,h.height*.34));
  await page.waitForTimeout(680);
  records.push({layer,pose:[yaw,pitch],state:await owl.evaluate(e=>({...e.dataset}))});
  await page.screenshot({path:path.join(out,`pose-${String(i).padStart(2,'0')}-${layer}.png`),clip:b});
 }
}
await fs.writeFile(path.join(out,'poses.json'),JSON.stringify(records,null,2));
await browser.close();

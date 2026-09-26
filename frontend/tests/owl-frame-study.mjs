// Native-resolution review of the SAME renderer; pointer regression is separate.
import {chromium} from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';
const out=path.resolve('evidence/owl-diagonal-repair',process.env.OWL_EVIDENCE||'native-before');await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--enable-gpu','--use-gl=angle','--use-angle=gl']});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
await page.goto('http://127.0.0.1:4180/'+(process.env.OWL_CANDIDATE==='1'?'?owlCandidate=1':''));
await page.evaluate(async()=>{const {createOwlSurface}=await import('/src/components/owlSurface.ts');const c=document.createElement('canvas');c.width=1163;c.height=1353;document.body.replaceChildren(c);window.study={canvas:c,surface:await createOwlSurface(c,new AbortController().signal)};});
const manifest=JSON.parse(await fs.readFile(`public/assets/owl/${process.env.OWL_CANDIDATE==='1'?'diagonal-candidate':'smooth-field'}/manifest.json`,'utf8'));
const poses=process.env.OWL_FULL==='1'?[...manifest.views.map(v=>[v.yaw,v.pitch]),...Array.from({length:48},(_,i)=>[Math.cos(i*Math.PI/24)*21,Math.sin(i*Math.PI/24)*12.6]),...Array.from({length:13},(_,i)=>[i*1.25,i*.75]),...Array.from({length:13},(_,i)=>[-i*1.25,-i*.75])]:[[7.5,4.5],[-7.5,-4.5],[12,7.2],[-12,-7.2]];
for(const [i,[yaw,pitch]] of poses.entries()){
 const png=await page.evaluate(({yaw,pitch})=>{const s=window.study;s.surface.draw(yaw,pitch);return s.canvas.toDataURL('image/png').split(',')[1];},{yaw,pitch});
 await fs.writeFile(path.join(out,`pose-${String(i).padStart(3,'0')}.png`),Buffer.from(png,'base64'));
}
await fs.writeFile(path.join(out,'poses.json'),JSON.stringify(poses));await browser.close();

import {chromium} from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';
const neck=process.env.OWL_NECK==='1',field=neck?'neck-candidate':'smooth-field';
const url=`http://127.0.0.1:4180/?owlDebug=1${neck?'&owlNeck=1':''}`;
const out=path.resolve(import.meta.dirname,neck?'../evidence/owl-neck-continuity/lifecycle':'../evidence/owl-diagonal-repair/final-lifecycle');await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--enable-gpu','--use-gl=angle','--use-angle=gl']});
const context=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:2});
const page=await context.newPage(),checks=[],errors=[];
page.on('pageerror',e=>errors.push(e.message));
const check=(name,pass,detail)=>{checks.push({name,status:pass?'PASS':'FAIL',detail});console.log(checks.at(-1));};
try{
 await page.goto(url);await page.waitForFunction(()=>document.querySelector('.owl-art')?.dataset.renderer==='continuous-surface');
 const owl=page.locator('.winter-hero .owl-art');
 await page.mouse.move(1080,280);await page.waitForTimeout(650);
 const expected=async()=>owl.evaluate(e=>{const b=e.getBoundingClientRect(),h=e.closest('.winter-hero').getBoundingClientRect();let x=(1080-b.x-b.width*497.5/1163)/Math.max(155,h.width*.34),y=(b.y+b.height*260/1353-280)/Math.max(115,h.height*.34);let r=Math.hypot(x,y);if(r>1){x/=r;y/=r;}return{yaw:x*30,pitch:y*18,actual:{...e.dataset},canvas:{width:e.querySelector('canvas').width,height:e.querySelector('canvas').height,dpr:devicePixelRatio}};});
 let e=await expected();check('High-DPI source-resolution cap',e.canvas.width===1163&&e.canvas.dpr===2,e.canvas);
 await page.evaluate(()=>scrollTo(0,100));await page.waitForTimeout(700);e=await expected();check('Stationary cursor remaps after scroll',Math.abs(+e.actual.yaw-e.yaw)<.01&&Math.abs(+e.actual.pitch-e.pitch)<.01,e);
 await page.setViewportSize({width:1366,height:900});await page.waitForTimeout(700);e=await expected();check('Stationary cursor remaps after resize',Math.abs(+e.actual.yaw-e.yaw)<.01&&Math.abs(+e.actual.pitch-e.pitch)<.01,e);
 await page.emulateMedia({reducedMotion:'reduce'});await page.waitForTimeout(80);check('Reduced-motion toggle restores poster',await owl.evaluate(e=>!e.classList.contains('has-frames')));
 await page.emulateMedia({reducedMotion:'no-preference'});await page.waitForTimeout(160);check('Leaving reduced motion resumes renderer',await owl.evaluate(e=>e.classList.contains('has-frames')));
 await page.evaluate(()=>scrollTo(0,0));await page.locator('.winter-hero').getByRole('link',{name:'Get started',exact:true}).hover();await page.waitForTimeout(650);
 check('Get started hover uses live head tracking without navigation',await owl.evaluate(e=>+e.dataset.yaw<0&&e.classList.contains('has-frames')));
 // Simulated visibility events test our handler. This is not a real-device
 // background-tab performance measurement.
 await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));});
 const count=await owl.getAttribute('data-draw-count');await page.mouse.move(600,300);await page.waitForTimeout(150);check('Simulated hidden tab pauses drawing',count===await owl.getAttribute('data-draw-count'));
 await page.evaluate(()=>{delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));});await page.waitForTimeout(250);check('Visibility return resumes drawing',count!==await owl.getAttribute('data-draw-count'));
 await page.screenshot({path:path.join(out,'high-dpi.png')});
 await owl.locator('canvas').evaluate(c=>c.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());await page.waitForTimeout(100);check('Context loss restores static fallback',await owl.evaluate(e=>e.dataset.fallback==='graphics-context-lost'&&!e.classList.contains('has-frames')));
 const loading=await context.newPage();let release;const gate=new Promise(resolve=>release=resolve);
 await loading.route(`**/assets/owl/${field}/manifest.json`,async route=>{await gate;await route.continue().catch(()=>{});});
 await loading.goto(url,{waitUntil:'domcontentloaded'});
 await loading.waitForFunction(()=>document.querySelector('.owl-art')?.dataset.loading==='true');
 await loading.locator('.owl-art canvas').evaluate(c=>c.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());release();await loading.waitForTimeout(800);
 check('Context loss during load cannot reveal late canvas',await loading.locator('.owl-art').evaluate(e=>e.dataset.fallback==='graphics-context-lost'&&!e.classList.contains('has-frames')));
 check('No JavaScript exceptions',errors.length===0,errors);
}catch(error){checks.push({name:'Execution',status:'FAIL',detail:error.stack});console.error(error);}
await fs.writeFile(path.join(out,'results.json'),JSON.stringify({checks,errors,headless:true,browser:await browser.version(),visibilityTest:'synthetic document.hidden + visibilitychange, not native OS tab switching'},null,2));await browser.close();if(checks.some(c=>c.status==='FAIL'))process.exitCode=1;

import {chromium} from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'evidence/owl-smooth-v2',process.env.OWL_EVIDENCE||'browser-final');await fs.mkdir(out,{recursive:true});
const candidate=process.env.OWL_CANDIDATE==='1',software=process.env.OWL_CANVAS==='1';
const field=candidate?'diagonal-candidate':'smooth-field';
const url='http://127.0.0.1:4180/?owlDebug=1'+(candidate?'&owlCandidate=1':'')+(software?'&owlCanvas=1':'');
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:process.env.OWL_HEADED!=='1',args:['--no-sandbox',...(process.env.OWL_HEADED==='1'||process.env.OWL_GPU==='1'?['--enable-gpu','--use-gl=angle','--use-angle=gl']:[])]});
const page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1});
const errors=[],checks=[],warnings=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());if(m.type()==='warning')warnings.push(m.text());});
const check=(name,pass,detail)=>{checks.push({name,status:pass?'PASS':'FAIL',detail});console.log(pass?'PASS':'FAIL',name);};
const stat=values=>{const v=[...values].sort((a,b)=>a-b);return{count:v.length,median:v[Math.floor(v.length*.5)],p95:v[Math.floor(v.length*.95)],max:v.at(-1)};};
const owl=page.locator('.winter-hero .owl-art');const samples=()=>owl.evaluate(e=>e.owlSamples);const state=()=>owl.evaluate(e=>({...e.dataset}));
let metrics={};
try{
 const start=Date.now();await page.goto(url);await page.waitForFunction(()=>document.querySelector('.owl-art')?.dataset.renderer==='continuous-surface');metrics.firstInteractiveMs=Date.now()-start;metrics.info=await owl.evaluate(e=>e.owlInfo);
 const coordinate=async(yaw,pitch)=>{const box=await owl.boundingBox(),hero=await page.locator('.winter-hero').boundingBox();return{x:box.x+box.width*497.5/1163+yaw/30*Math.max(155,hero.width*.34),y:box.y+box.height*260/1353-pitch/18*Math.max(115,hero.height*.34)};};
 const move=async(yaw,pitch,steps=1)=>{const p=await coordinate(yaw,pitch);await page.mouse.move(p.x,p.y,{steps});};
 const poses=[[0,0],[10.5,0],[9.1,3.15],[5.25,5.46],[0,6.3],[-5.25,5.46],[-10.5,0],[-5.25,-5.46],[5.25,-5.46],[19.5,0],[16.89,5.85],[9.75,10.13],[-9.75,10.13],[-19.5,0],[-9.75,-10.13],[19.5,-5.85],[7.5,4.5],[12,7.2],[-7.5,-4.5],[-12,-7.2]];
 const holds=[];
 for(const [i,pose] of poses.entries()){await move(...pose);await page.waitForTimeout(650);holds.push({intended:pose,state:await state()});await page.screenshot({path:path.join(out,`hold-${String(i).padStart(2,'0')}.png`),clip:await owl.boundingBox()});}
 await fs.writeFile(path.join(out,'holds.json'),JSON.stringify(holds,null,2));
 check('Every screenshot holds its requested pose',holds.every(h=>Math.abs(+h.state.yaw-h.intended[0])<.03&&Math.abs(+h.state.pitch-h.intended[1])<.03),holds);
 // Record the actual live renderer's canvas at up to display cadence. These
 // are not separately generated animation frames or an interpolated MP4.
 await page.evaluate(()=>{const c=document.querySelector('.owl-art canvas');const stream=c.captureStream(60);const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp9',videoBitsPerSecond:12000000});window.owlRecording={recorder,stream,chunks:[]};recorder.ondataavailable=e=>{if(e.data.size)window.owlRecording.chunks.push(e.data);};recorder.start();document.querySelector('.owl-art').owlSamples.length=0;});
 const pathStart=await page.evaluate(()=>performance.now());
 for(const radius of [.17,.43,.70])for(const dir of [1,-1])for(let i=0;i<120;i++){const a=dir*i/120*Math.PI*2;await move(Math.cos(a)*30*radius,Math.sin(a)*18*radius);await page.waitForTimeout(12);}
 for(let i=0;i<150;i++){const a=i/149*Math.PI*4;await move(Math.sin(a)*22,Math.sin(a*2)*10);await page.waitForTimeout(12);}
 for(const p of [[-23,9],[23,-9],[-23,-9],[23,9],[0,0],[13.123,-4.567]]){await move(...p);await page.waitForTimeout(240);}
 await page.waitForTimeout(550);
 const motionSamples=await samples();const intervals=motionSamples.slice(1).map((s,i)=>s.time-motionSamples[i].time);
 metrics.actualDrawIntervals=stat(intervals.filter(v=>v<1000));metrics.submitCostMs=stat(motionSamples.map(s=>s.drawMs));metrics.actualDraws=motionSamples.length;metrics.durationMs=await page.evaluate(()=>performance.now())-pathStart;metrics.distinctRenderedPoses=new Set(motionSamples.map(s=>`${s.yaw.toFixed(4)},${s.pitch.toFixed(4)}`)).size;
 check('Actual changing canvas is drawn at display cadence',metrics.actualDrawIntervals.median<20&&metrics.actualDrawIntervals.p95<25,metrics.actualDrawIntervals);
 check('Hundreds of distinct rendered intermediate poses',metrics.distinctRenderedPoses>800,metrics.distinctRenderedPoses);
 check('Arbitrary intermediate hold is unquantized',Math.abs(+(await state()).yaw-13.123)<.02&&Math.abs(+(await state()).pitch+4.567)<.02,await state());
 const recording=await page.evaluate(()=>new Promise(resolve=>{const r=window.owlRecording;r.recorder.onstop=()=>{r.stream.getTracks().forEach(t=>t.stop());const blob=new Blob(r.chunks,{type:'video/webm'});const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.readAsDataURL(blob);};r.recorder.stop();}));await fs.writeFile(path.join(out,'actual-canvas-motion.webm'),Buffer.from(recording,'base64'));
 await fs.writeFile(path.join(out,'actual-draw-samples.json'),JSON.stringify(motionSamples));
 const a=await state();await page.waitForTimeout(350);const b=await state();check('Settled pose stops drawing',a.drawCount===b.drawCount,{a:a.drawCount,b:b.drawCount});
 await page.evaluate(()=>scrollTo(0,500));await page.mouse.move(100,700);await page.waitForTimeout(750);check('Pointer leave returns to neutral',Math.abs(+(await state()).yaw)<.1&&Math.abs(+(await state()).pitch)<.1,await state());
 await page.evaluate(()=>scrollTo(0,0));await page.setViewportSize({width:1366,height:768});await page.waitForTimeout(180);await move(-11.234,6.543);await page.waitForTimeout(650);check('Laptop resize keeps relative mapping',Math.abs(+(await state()).yaw+11.234)<.1,await state());await page.screenshot({path:path.join(out,'laptop-1366.png')});
 await page.setViewportSize({width:1920,height:1080});await page.waitForTimeout(150);await move(12,-4);await page.waitForTimeout(650);await page.screenshot({path:path.join(out,'desktop-1920.png')});
 await page.setViewportSize({width:1024,height:768});await page.waitForTimeout(150);await move(-12,4);await page.waitForTimeout(650);await page.screenshot({path:path.join(out,'tablet-1024.png')});
 await page.evaluate(()=>scrollTo(0,document.body.scrollHeight));await page.waitForTimeout(200);const before=(await state()).drawCount;await page.waitForTimeout(250);check('Offscreen drawing pauses',before===(await state()).drawCount,{before,after:(await state()).drawCount});
 const reduced=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});const rp=await reduced.newPage();let requests=0;rp.on('request',r=>{if(r.url().includes(field))requests++;});await rp.goto(url);await rp.waitForTimeout(350);check('Reduced motion makes no field requests',requests===0,requests);await reduced.close();
 const mobile=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true});const mp=await mobile.newPage();requests=0;mp.on('request',r=>{if(r.url().includes(field))requests++;});await mp.goto(url);await mp.waitForTimeout(350);check('Touch remains static without field requests',requests===0,requests);await mp.screenshot({path:path.join(out,'mobile-390.png')});await mobile.close();
 metrics.resources=await page.evaluate(field=>performance.getEntriesByType('resource').filter(e=>e.name.includes(field)).reduce((s,e)=>({requests:s.requests+1,bytes:s.bytes+e.encodedBodySize,transfer:s.transfer+e.transferSize}),{requests:0,bytes:0,transfer:0}),field);check('No runtime errors',errors.length===0,errors);
 const fallback=await browser.newContext({viewport:{width:1440,height:900}});const fp=await fallback.newPage();await fp.route(`**/assets/owl/${field}/manifest.json`,r=>r.fulfill({status:404,body:'deliberate fallback test'}));await fp.goto(url);await fp.waitForTimeout(300);check('Missing asset keeps static fallback visible',await fp.locator('.owl-art').evaluate(e=>e.dataset.fallback==='surface-unavailable'&&!e.classList.contains('has-frames')));await fallback.close();
}catch(error){checks.push({name:'Test execution',status:'FAIL',detail:error.stack});console.error(error);}
await fs.writeFile(path.join(out,'results.json'),JSON.stringify({browser:await browser.version(),headless:process.env.OWL_HEADED!=='1',metrics,checks,errors,warnings},null,2));await browser.close();
if(checks.some(c=>c.status==='FAIL'))process.exitCode=1;

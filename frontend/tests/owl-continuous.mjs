import {chromium} from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';

const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'evidence/owl-browser-review');
await fs.mkdir(out,{recursive:true});
const base=process.env.STETHOFUSE_TEST_URL||'http://127.0.0.1:4180';
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const errors=[],responses=[],checks=[];
const check=(name,pass,detail)=>{checks.push({name,status:pass?'PASS':'FAIL',detail});console.log(`${pass?'PASS':'FAIL'} ${name}`);};
const context=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1,recordVideo:{dir:out,size:{width:1440,height:900}}});
const page=await context.newPage();
const metrics={};
page.on('pageerror',error=>errors.push(error.message));
page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
page.on('response',response=>{responses.push({url:response.url(),status:response.status()});if(response.status()>=400)errors.push(`${response.status()} ${response.url()}`);});

const owl=page.locator('.winter-hero .owl-art');
const state=()=>owl.evaluate(element=>({yaw:+element.dataset.yaw,pitch:+element.dataset.pitch,targetYaw:+element.dataset.targetYaw,targetPitch:+element.dataset.targetPitch,frame:element.dataset.frame,cache:+element.dataset.cached,visible:element.classList.contains('has-frames'),fallback:element.dataset.fallback||''}));
const settle=async(ms=520)=>{await page.waitForTimeout(ms);return state();};

try{
 const coldStart=Date.now();await page.goto(`${base}/?owlDebug=1`,{waitUntil:'domcontentloaded'});
 await page.locator('h1').waitFor();
 await owl.waitFor();
 await page.waitForFunction(()=>document.querySelector('.owl-art')?.classList.contains('has-frames'));
 metrics.firstInteractiveOwlMs=Date.now()-coldStart;
 const box=await owl.boundingBox();if(!box)throw new Error('Owl has no layout box');
 const center={x:box.x+box.width*(497.5/1163),y:box.y+box.height*(260/1353)};
 check('Live renderer starts on dense pose field',(await state()).frame==='20-12',await state());
 check('Legacy eight-route state is absent',await owl.getAttribute('data-route')===null,await owl.getAttribute('data-route'));

 const timingPromise=page.evaluate(()=>new Promise(resolve=>{const intervals=[];let previous=0,start=0;const sample=time=>{if(!start)start=time;if(previous)intervals.push(time-previous);previous=time;if(time-start<2200)requestAnimationFrame(sample);else resolve(intervals);};requestAnimationFrame(sample);}));
 for(let index=0;index<90;index++){const angle=index/89*Math.PI*4;await page.mouse.move(center.x+Math.sin(angle)*250,center.y+Math.sin(angle*2)*125,{steps:1});await page.waitForTimeout(20);}
 const intervals=await timingPromise;intervals.sort((a,b)=>a-b);metrics.frameTiming={samples:intervals.length,medianMs:intervals[Math.floor(intervals.length*.5)],p95Ms:intervals[Math.floor(intervals.length*.95)],maxMs:intervals.at(-1)};
 check('Animation loop remains near display cadence',metrics.frameTiming.medianMs<20&&metrics.frameTiming.p95Ms<28,metrics.frameTiming);

 const radii=[55,145,285],circleEvidence=[];
 for(const [radiusIndex,radius] of radii.entries()){
  for(const clockwise of [true,false]){
   const samples=[];
   for(let index=0;index<72;index++){
    const angle=(clockwise?1:-1)*Math.PI*2*index/72;
    await page.mouse.move(center.x+Math.cos(angle)*radius,center.y+Math.sin(angle)*radius,{steps:1});
    await page.waitForTimeout(20);
    if(index%6===0)samples.push(await state());
   }
   await page.waitForTimeout(240);
   samples.push(await state());
   circleEvidence.push({radius,direction:clockwise?'clockwise':'counterclockwise',samples});
  }
 }
 const circleFrames=circleEvidence.flatMap(run=>run.samples.map(sample=>sample.frame));
 const smallAmplitude=Math.max(...circleEvidence[0].samples.map(sample=>Math.hypot(sample.targetYaw/30,sample.targetPitch/18)));
 const largeAmplitude=Math.max(...circleEvidence[4].samples.map(sample=>Math.hypot(sample.targetYaw/30,sample.targetPitch/18)));
 check('Clockwise and counterclockwise circles use many intermediate poses',new Set(circleFrames).size>=35,{unique:new Set(circleFrames).size});
 check('Cursor radius scales motion amplitude',largeAmplitude>smallAmplitude*2,{smallAmplitude,largeAmplitude});

 const holds=[];
 for(const [dx,dy] of [[.37,-.21],[-.43,-.31],[.56,.42],[-.18,.53]]){
  await page.mouse.move(center.x+dx*285,center.y+dy*240,{steps:18});
  holds.push(await settle(620));
 }
 check('Arbitrary non-anchor holds remain stable',holds.every(sample=>Number.isFinite(sample.yaw)&&Number.isFinite(sample.pitch)&&sample.frame),holds);
 await owl.screenshot({path:path.join(out,'intermediate-hold-closeup.png')});

 const sweep=[];
 for(const [dx,dy] of [[-280,-150],[280,150],[-280,150],[280,-150],[-20,10],[270,0],[-270,0]]){
  await page.mouse.move(center.x+dx,center.y+dy,{steps:dx===-20?3:5});
  await page.waitForTimeout(120);sweep.push(await state());
 }
 check('Abrupt reversals stay in the continuous field',new Set(sweep.map(sample=>sample.frame)).size>=5,sweep);

 await page.mouse.move(center.x,center.y,{steps:20});
 const neutral=await settle(700);
 check('Pointer between the eyes returns to exact neutral',Math.abs(neutral.yaw)<.08&&Math.abs(neutral.pitch)<.08&&neutral.frame==='20-12',neutral);
 await page.screenshot({path:path.join(out,'hero-neutral-1440.png')});

 await page.mouse.move(center.x+245,center.y-118,{steps:25});await settle(520);await page.screenshot({path:path.join(out,'hero-up-right-intermediate-1440.png')});
 await page.mouse.move(center.x-215,center.y+93,{steps:25});await settle(520);await page.screenshot({path:path.join(out,'hero-down-left-intermediate-1440.png')});

 // Scroll while the owl is still substantially visible, then move the real
 // pointer into the following section. This crosses the hero boundary instead
 // of merely moving to another coordinate still inside the 900px hero.
 await page.evaluate(()=>window.scrollTo(0,500));await page.waitForTimeout(120);await page.mouse.move(100,700,{steps:12});const leave=await settle(850);
 check('Pointer leaving hero returns smoothly toward neutral',Math.abs(leave.yaw)<.15&&Math.abs(leave.pitch)<.15,leave);
 await page.evaluate(()=>window.scrollTo(0,0));await page.waitForTimeout(180);
 await page.setViewportSize({width:1024,height:768});await page.waitForTimeout(300);const resizedBox=await owl.boundingBox();await page.mouse.move(900,180,{steps:15});const resized=await settle(600);
 check('Tracking remains mapped after resize',!!resizedBox&&resized.yaw>4&&resized.pitch>0,{resizedBox,resized});

 await page.evaluate(()=>window.scrollTo(0,document.body.scrollHeight));await page.waitForTimeout(450);const before=responses.filter(item=>item.url.includes('/continuous-field/pose-')).length;await page.waitForTimeout(650);const after=responses.filter(item=>item.url.includes('/continuous-field/pose-')).length;
 check('Offscreen renderer pauses network work',before===after,{before,after});

 const fieldResponses=responses.filter(item=>item.url.includes('/continuous-field/pose-'));
 metrics.resources=await page.evaluate(()=>performance.getEntriesByType('resource').filter(entry=>entry.name.includes('/continuous-field/pose-')).reduce((result,entry)=>({count:result.count+1,transferBytes:result.transferBytes+entry.transferSize,encodedBytes:result.encodedBytes+entry.encodedBodySize,durationMs:result.durationMs+entry.duration}),{count:0,transferBytes:0,encodedBytes:0,durationMs:0}));
 check('Decoded cache remains bounded',(await state()).cache<=16,await state());
 check('Normal owl assets have no HTTP errors',fieldResponses.length>0&&fieldResponses.every(item=>item.status===200),{count:fieldResponses.length,bad:fieldResponses.filter(item=>item.status!==200)});

 const reduced=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});const reducedPage=await reduced.newPage();const reducedRequests=[];reducedPage.on('request',request=>reducedRequests.push(request.url()));await reducedPage.goto(base);await reducedPage.locator('h1').waitFor();await reducedPage.mouse.move(1300,180);await reducedPage.waitForTimeout(500);check('Reduced motion keeps the approved static poster',!reducedRequests.some(url=>url.includes('/continuous-field/')),reducedRequests.filter(url=>url.includes('/continuous-field/')));await reduced.close();
 const touch=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true});const touchPage=await touch.newPage();const touchRequests=[];touchPage.on('request',request=>touchRequests.push(request.url()));await touchPage.goto(base);await touchPage.locator('h1').waitFor();await touchPage.waitForTimeout(500);await touchPage.screenshot({path:path.join(out,'mobile-static-fallback-390.png'),fullPage:true});check('Touch fallback does not load pose field',!touchRequests.some(url=>url.includes('/continuous-field/')),touchRequests.filter(url=>url.includes('/continuous-field/')));await touch.close();
 check('No normal-browser console or page errors',errors.length===0,errors);
 await fs.writeFile(path.join(out,'circle-samples.json'),JSON.stringify(circleEvidence,null,2));
}catch(error){checks.push({name:'Owl browser test execution',status:'FAIL',detail:error.stack});console.error(error);}
const video=page.video();
await context.close();
const videoPath=video?await video.path():null;
if(videoPath)await fs.copyFile(videoPath,path.join(out,'owl-circular-tracking.webm'));
await fs.writeFile(path.join(out,'results.json'),JSON.stringify({testedAt:new Date().toISOString(),browser:await browser.version(),base,checks,errors,metrics,video:path.join(out,'owl-circular-tracking.webm')},null,2));
await browser.close();
if(checks.some(item=>item.status==='FAIL'))process.exitCode=1;

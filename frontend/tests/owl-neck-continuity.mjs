// The actual pointer controller and surface, not a separate animation demo.
import {chromium} from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';
const name=process.env.OWL_NECK==='1'?'after':'before',software=process.env.OWL_CANVAS==='1';
const out=path.resolve(`evidence/owl-neck-continuity/${name}${software?'-canvas':''}`);await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--enable-gpu','--use-gl=angle','--use-angle=gl']});
const dpr=Number(process.env.OWL_DPR||2);
const page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:dpr});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(`http://127.0.0.1:4180/?owlDebug=1${name==='after'?'&owlNeck=1':''}${software?'&owlCanvas=1':''}`);
await page.waitForFunction(()=>document.querySelector('.owl-art')?.dataset.renderer==='continuous-surface');
// Snapshot surface uses exactly the same module, drawing synchronously before
// WebGL discards its default framebuffer. Live pointer/motion tests stay on
// the real page. Blank toDataURL output must never count as stable body pixels.
await page.evaluate(async()=>{const {createOwlSurface}=await import('/src/components/owlSurface.ts');const canvas=document.createElement('canvas');canvas.width=1163;canvas.height=1353;window.poseCapture={canvas,surface:await createOwlSurface(canvas,new AbortController().signal)};});
const owl=page.locator('.winter-hero .owl-art');
const move=async(yaw,pitch)=>{const b=await owl.boundingBox(),h=await page.locator('.winter-hero').boundingBox();await page.mouse.move(b.x+b.width*497.5/1163+yaw/30*Math.max(155,h.width*.34),b.y+b.height*260/1353-pitch/18*Math.max(115,h.height*.34));};
const poses=[[0,-12],[-6,-12],[-12,-12],[-18,-10],[-22,-5],[-24,0],[-15,-9],[-12,-7.2],[-7.5,-4.5],[12,7.2],[0,0]],holds=[];
for(const [i,p] of poses.entries()){
 await move(...p);await page.waitForTimeout(650);
 const data=await owl.evaluate(e=>{const c=window.poseCapture;c.surface.draw(+e.dataset.yaw,+e.dataset.pitch);return {png:c.canvas.toDataURL('image/png').split(',')[1],state:{...e.dataset},info:e.owlInfo};});
 await fs.writeFile(path.join(out,`pose-${String(i).padStart(2,'0')}.png`),Buffer.from(data.png,'base64'));holds.push({pose:p,state:data.state,info:data.info});
}
await page.screenshot({path:path.join(out,'website.png')});
await page.evaluate(()=>window.poseCapture.surface.dispose());
await page.evaluate(()=>{const c=document.querySelector('.owl-art canvas'),stream=c.captureStream(60),r=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp9',videoBitsPerSecond:14000000});window.record={stream,r,chunks:[]};r.ondataavailable=e=>{if(e.data.size)window.record.chunks.push(e.data)};r.start();document.querySelector('.owl-art').owlSamples.length=0;});
for(let lap=0;lap<2;lap++){
 for(let i=0;i<180;i++){const a=-Math.PI/2-i/179*Math.PI/2;await move(24*Math.cos(a),12*Math.sin(a));await page.waitForTimeout(16);}
 for(let i=0;i<180;i++){const a=-Math.PI+i/179*Math.PI/2;await move(24*Math.cos(a),12*Math.sin(a));await page.waitForTimeout(16);}
}
const recording=await page.evaluate(()=>new Promise(resolve=>{const r=window.record;r.r.onstop=()=>{r.stream.getTracks().forEach(t=>t.stop());const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.readAsDataURL(new Blob(r.chunks,{type:'video/webm'}));};r.r.stop();}));
await fs.writeFile(path.join(out,'down-left-turn.webm'),Buffer.from(recording,'base64'));
const samples=await owl.evaluate(e=>e.owlSamples);const values=samples.slice(1).map((s,i)=>s.time-samples[i].time).sort((a,b)=>a-b),costs=samples.map(s=>s.drawMs).sort((a,b)=>a-b);
const report={holds,errors,actualDraws:samples.length,medianMs:values[Math.floor(values.length*.5)],p95Ms:values[Math.floor(values.length*.95)],maxMs:values.at(-1),drawP95Ms:costs[Math.floor(costs.length*.95)],browser:await browser.version(),headless:true,viewport:[1440,900],dpr};
await fs.writeFile(path.join(out,'results.json'),JSON.stringify(report,null,2));await browser.close();console.log(JSON.stringify({...report,holds:holds.map(h=>({pose:h.pose,actual:[h.state.yaw,h.state.pitch]}))},null,2));if(errors.length)process.exitCode=1;

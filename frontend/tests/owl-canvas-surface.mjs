import {chromium} from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';

const root=path.resolve(import.meta.dirname,'..');
const candidate=process.env.OWL_CANDIDATE==='1';
const out=path.join(root,'output/playwright',candidate?'owl-canvas-candidate':'owl-canvas');await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:process.env.OWL_HEADED!=='1',args:['--no-sandbox','--disable-gpu']});
const page=await browser.newPage({viewport:{width:1280,height:900},deviceScaleFactor:1});
const errors=[];page.on('pageerror',error=>errors.push(error.message));
const checks=[],check=(name,passed,detail)=>{checks.push({name,passed,detail});console.log(passed?'PASS':'FAIL',name,JSON.stringify(detail));};
const summarize=values=>{const sorted=[...values].sort((a,b)=>a-b);return{count:values.length,median:sorted[Math.floor(sorted.length*.5)],p95:sorted[Math.floor(sorted.length*.95)],max:sorted.at(-1)};};
try{
 await page.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl'||type==='webgl2'?null:original.call(this,type,...args);};});
 await page.route('**/__owl_canvas_test*',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><html><body style="margin:0;background:#f5f0e7"><canvas width="590" height="686" style="width:590px;height:686px"></canvas></body></html>'}));
 await page.goto(`http://127.0.0.1:4180/__owl_canvas_test${candidate?'?owlCandidate=1':''}`);
 const init=await page.evaluate(async()=>{const {createOwlCanvasSurface}=await import('/src/components/owlCanvasSurface.ts');const canvas=document.querySelector('canvas'),start=performance.now();window.surface=await createOwlCanvasSurface(canvas,new AbortController().signal);window.surface.draw(0,0);return{initializationMs:performance.now()-start,webglUnavailable:canvas.getContext('webgl2')===null,info:window.surface.info};});
 check('Canvas2D surface loads with WebGL2 deliberately null',init.webglUnavailable,init);
 const neutralComparison=await page.evaluate(async()=>{
  const base=new URLSearchParams(location.search).has('owlCandidate')?'/assets/owl/diagonal-candidate/':'/assets/owl/smooth-field/';
  const manifest=await(await fetch(base+'manifest.json')).json(),image=await createImageBitmap(await(await fetch(base+manifest.views[0].texture)).blob());
  const canvas=document.querySelector('canvas'),reference=document.createElement('canvas');reference.width=canvas.width;reference.height=canvas.height;
  const ctx=reference.getContext('2d');ctx.drawImage(image,0,0,canvas.width,canvas.height*600/1353);image.close();
  const actual=canvas.getContext('2d').getImageData(0,0,590,220).data,expected=ctx.getImageData(0,0,590,220).data;
  // Compare the opaque interior; the silhouette is resampled twice by the
  // fallback's head buffer, so its fractional edge coverage can differ.
  let opaque=0,alphaHoles=0,rgbError=0,maxAlpha=0;for(let y=2;y<218;y++)for(let x=2;x<588;x++){
   const i=(y*590+x)*4;maxAlpha=Math.max(maxAlpha,expected[i+3]);let interior=true;
   for(let dy=-2;dy<=2&&interior;dy++)for(let dx=-2;dx<=2;dx++)if(expected[((y+dy)*590+x+dx)*4+3]<=240){interior=false;break;}
   if(interior){opaque++;if(actual[i+3]<expected[i+3]-5)alphaHoles++;rgbError+=Math.abs(actual[i]-expected[i])+Math.abs(actual[i+1]-expected[i+1])+Math.abs(actual[i+2]-expected[i+2]);}
  }
  return{opaquePixels:opaque,maxAlpha,alphaHoles,meanRgbError:rgbError/opaque/3};
 });
 check('Shared triangle edges leave no alpha cracks in the neutral head',neutralComparison.opaquePixels>10000&&neutralComparison.alphaHoles===0,neutralComparison);
 const assetsBefore=await page.evaluate(()=>performance.getEntriesByType('resource').length);
 const poses=[[0,0],[8,4],[-8,4],[8,-4],[-8,-4],[19,7],[-19,-7],[13.123,-4.567],[12,7.2],[-12,-7.2]];
 const hashes=[],bodyHashes=[];
 for(const [index,pose] of poses.entries()){
  const result=await page.evaluate(([yaw,pitch])=>{window.surface.draw(yaw,pitch);const canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d'),head=ctx.getImageData(0,0,canvas.width,300).data,body=ctx.getImageData(0,400,canvas.width,200).data;const hash=data=>{let value=2166136261;for(let i=0;i<data.length;i++)value=Math.imul(value^data[i],16777619);return value>>>0;};return{head:hash(head),body:hash(body),cornerAlpha:ctx.getImageData(0,0,1,1).data[3]};},pose);
  hashes.push(result.head);bodyHashes.push(result.body);check(`Pose ${pose.join(', ')} has transparent background`,result.cornerAlpha===0,result);
  await page.locator('canvas').screenshot({path:path.join(out,`pose-${index}.png`)});
 }
 check('Intermediate poses produce distinct rendered pixels',new Set(hashes).size===poses.length,hashes);
 check('Body stays pixel-identical through every pose',new Set(bodyHashes).size===1,bodyHashes);
 const timing=await page.evaluate(async()=>{
  for(let i=0;i<30;i++)window.surface.draw(10+Math.sin(i/20)*3,3+Math.cos(i/20)*2);
  const samples=[];let last;
  for(let i=0;i<240;i++)await new Promise(resolve=>requestAnimationFrame(time=>{const start=performance.now();window.surface.draw(Math.sin(i/40)*21+1.123,Math.cos(i/40)*10+1.456);samples.push({drawMs:performance.now()-start,interval:last?time-last:0});last=time;resolve();}));
  return samples;
 });
 const drawMs=summarize(timing.map(sample=>sample.drawMs)),intervals=summarize(timing.slice(1).map(sample=>sample.interval));
 check('590-pixel changing head draws within a 60 fps frame budget',drawMs.p95<16.7,drawMs);
 check('Actual animation runs at display cadence',intervals.median<20&&intervals.p95<25,intervals);
 const assetsAfter=await page.evaluate(()=>performance.getEntriesByType('resource').length);
 check('Pointer-era drawing performs no network requests',assetsAfter===assetsBefore,{before:assetsBefore,after:assetsAfter});
 await page.evaluate(()=>{const canvas=document.querySelector('canvas');canvas.width=1163;canvas.height=1353;window.surface.resize();window.surface.draw(12.345,6.789);});
 check('Retina-sized canvas keeps the documented 590-pixel head cap',await page.evaluate(()=>window.surface.info.headRasterWidth===590),await page.evaluate(()=>window.surface.info));
 await page.evaluate(()=>{window.surface.dispose();window.surface.dispose();window.surface.draw(0,0);});
 check('Double disposal and late draw are safe',errors.length===0,errors);
 await fs.writeFile(path.join(out,'results.json'),JSON.stringify({browser:await browser.version(),checks,init,drawMs,intervals,timing,errors},null,2));
}finally{await browser.close();}
if(checks.some(check=>!check.passed))process.exitCode=1;

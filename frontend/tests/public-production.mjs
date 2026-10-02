import {build} from 'vite';
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

// Build separately: do not overwrite the coordinator's dist/ or preview server.
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const output=path.join(root,process.env.EVIDENCE_ROOT || 'evidence','public-production');
const built=path.join(root,'node_modules/.cache/stethofuse-public-production');
await mkdir(output,{recursive:true});
process.env.VITE_ENABLE_DEMO='false';
await build({root,mode:'production',build:{outDir:built,copyPublicDir:false,emptyOutDir:true},logLevel:'warn'});
const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.json':'application/json','.woff2':'font/woff2','.woff':'font/woff'};
const server=createServer(async(req,res)=>{
 try{
  const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  let bytes,filename;
  for(const folder of [built,path.join(root,'public')]){
   const candidate=path.resolve(folder,'.'+pathname);
   if(!candidate.startsWith(folder+path.sep))continue;
   try{bytes=await readFile(candidate);filename=candidate;break;}catch{}
  }
  if(!bytes){if(path.extname(pathname)){res.writeHead(404);res.end('Not found');return;}filename=path.join(built,'index.html');bytes=await readFile(filename);}
  res.writeHead(200,{'Content-Type':types[path.extname(filename)]||'application/octet-stream','Cache-Control':'no-store'});res.end(bytes);
 }catch{res.writeHead(500);res.end('Local test server error');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
const page=await context.newPage(),errors=[],results=[];
page.on('pageerror',e=>errors.push(e.message));
async function check(name,fn){try{await fn();results.push({name,status:'PASS'});console.log(`PASS ${name}`);}catch(e){results.push({name,status:'FAIL',error:e.message});console.error(`FAIL ${name}: ${e.message}`);}}
async function go(route){await page.goto(base+route,{waitUntil:'networkidle'});await page.locator('h1').first().waitFor();}
try{
 await check('Production welcome has no demo-persona link or inaccessible demo FAQ',async()=>{
  await go('/');assert.equal(await page.locator('a[href*="demo-personas"]').count(),0);
  assert.equal(await page.getByText('What can I try in the demonstration?',{exact:true}).count(),0);
  await page.getByText('How do I access my workspace?',{exact:true}).click();
  assert.equal(await page.getByRole('link',{name:'Check sign-in availability'}).getAttribute('href'),'/login');
  assert.ok(await page.getByText(/Authentication is not configured in this build/).isVisible());
  await page.locator('#support').screenshot({path:path.join(output,'faq-desktop.png')});
 });
 await check('Production FAQ destination exists without hidden persona target',async()=>{
  await page.getByRole('link',{name:'Check sign-in availability'}).click();
  await page.getByRole('button',{name:'Sign in',exact:true}).waitFor();
  assert.equal(new URL(page.url()).pathname,'/login');assert.equal(await page.locator('#demo-personas').count(),0);
  assert.equal(await page.getByText('Explore with a fictional demo account',{exact:false}).count(),0);
 });
 await check('Production auth callback does not suggest nonexistent demo accounts',async()=>{
  await go('/auth/callback?state=error');await page.getByRole('heading',{name:'Google is not connected.'}).waitFor();
  assert.equal(await page.locator('a[href*="demo-personas"]').count(),0);
  assert.equal((await page.locator('body').innerText()).includes('Use a fictional demo account'),false);
 });
 await check('Production ignores success previews and blocks demo workspace access',async()=>{
  await go('/register?state=success');assert.equal(await page.getByText('Demo registration preview',{exact:true}).count(),0);
  await go('/app/dashboard');assert.equal(new URL(page.url()).pathname,'/login');
 });
 await check('Narrow production FAQ remains usable and has no overflow',async()=>{
  await page.setViewportSize({width:390,height:844});await go('/');
  await page.getByText('How do I access my workspace?',{exact:true}).click();
  assert.ok(await page.getByRole('link',{name:'Check sign-in availability'}).isVisible());
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('#support').screenshot({path:path.join(output,'faq-mobile.png')});
 });
 await check('No production browser runtime errors',async()=>assert.deepEqual(errors,[]));
 const report={generatedAt:new Date().toISOString(),browser:await browser.version(),mode:'Separate normal production build; DEMO false; headless Chrome; reduced-motion; viewport emulation, not real device',results,errors,pass:results.filter(r=>r.status==='PASS').length,fail:results.filter(r=>r.status==='FAIL').length};
 await writeFile(path.join(output,'results.json'),JSON.stringify(report,null,2));
 process.exitCode=report.fail?1:0;
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}

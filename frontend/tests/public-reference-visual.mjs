import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
const output='evidence/public-reference/final';
await mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const results=[];
try {
  for (const size of [{width:1536,height:1024},{width:1366,height:768},{width:768,height:1024},{width:390,height:844}]) {
    const context=await browser.newContext({viewport:size,deviceScaleFactor:1,reducedMotion:'reduce'});
    const page=await context.newPage(),errors=[],failed=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('response',r=>{if(r.status()>=400)failed.push(`${r.status()} ${r.url()}`)});
    for (const [name,route] of [['login','/login'],['home','/'],...(size.width===390?[['register','/register'],['reset','/reset-password?state=expired']]:[])]) {
      const result={name,viewport:size,status:'PASS'};
      try {
        await page.goto('http://127.0.0.1:4180'+route);
        await page.locator('h1').waitFor();await page.evaluate(()=>document.fonts.ready);await page.waitForLoadState('networkidle');
        result.layout=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,card:document.querySelector('.auth-form')?.getBoundingClientRect().toJSON(),headline:document.querySelector('h1')?.getBoundingClientRect().toJSON(),gradient:getComputedStyle(document.querySelector('h1 em')||document.querySelector('h1')).backgroundImage,brokenImages:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src)}));
        assert.ok(result.layout.scroll<=size.width+1,'No page overflow');
        assert.deepEqual(result.layout.brokenImages,[]);assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);
        if(name==='login') {
          await page.getByLabel('Email address',{exact:true}).focus();await page.keyboard.press('Tab');assert.equal(await page.locator('input[name=password]').evaluate(e=>e===document.activeElement),true);
          await page.keyboard.press('Tab');assert.equal(await page.getByRole('button',{name:'Show password',exact:true}).evaluate(e=>e===document.activeElement),true);
          await page.getByRole('heading',{name:'Welcome back.'}).click();
        }
        await page.screenshot({path:`${output}/${name}-${size.width}.png`,fullPage:true});
      }catch(e){result.status='FAIL';result.error=e.message;process.exitCode=1;}
      results.push(result);console.log(result.name,size.width,result.status,result.error||'');
    }
    await context.close();
  }
}finally{await writeFile(`${output}/visual-checks.json`,JSON.stringify({browser:await browser.version(),conditions:'Localhost headless Chrome, emulated widths, DPR1, reduced motion; screenshots require separate visual review',results},null,2));await browser.close();}

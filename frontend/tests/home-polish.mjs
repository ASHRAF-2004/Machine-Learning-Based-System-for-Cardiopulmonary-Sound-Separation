import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {mkdir, writeFile} from 'node:fs/promises';

// Local, non-mutating presentation checks. Owl motion has its own regression suite.
const output = 'output/playwright/home-polish/responsive';
await mkdir(output, {recursive: true});
const browser = await chromium.launch({executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox']});
const results = [];
try {
  for (const viewport of [{width:1672,height:941},{width:1366,height:768},{width:768,height:1024},{width:390,height:844},{width:320,height:740}]) {
    const context = await browser.newContext({viewport, deviceScaleFactor:1, reducedMotion:'reduce'});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => {if(response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);});
    const result = {viewport, status:'PASS'};
    try {
      await page.goto('http://127.0.0.1:4180/');
      await page.locator('#welcome-title').waitFor();
      await page.evaluate(() => document.fonts.ready);
      await page.waitForLoadState('networkidle');
      result.layout = await page.evaluate(() => {
        const rect = selector => document.querySelector(selector).getBoundingClientRect().toJSON();
        const nav = getComputedStyle(document.querySelector('.public-nav'));
        return {width:innerWidth,scroll:document.documentElement.scrollWidth,nav:{background:nav.backgroundImage,color:nav.backgroundColor,blur:nav.backdropFilter,border:nav.borderBottomWidth},first:rect('h1>span'),second:rect('h1>em'),actions:rect('.hero-actions'),heading:rect('h1'),brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src)};
      });
      assert.ok(result.layout.scroll <= viewport.width, 'No horizontal page overflow');
      assert.equal(result.layout.nav.background, 'none', 'No header background image');
      assert.equal(result.layout.nav.color, 'rgba(0, 0, 0, 0)', 'Header is transparent');
      assert.equal(result.layout.nav.blur, 'none', 'No strip blurring the scene');
      assert.equal(result.layout.nav.border, '0px', 'No header dividing line');
      assert.ok(result.layout.actions.bottom < viewport.height, 'Both primary actions visible without scrolling');
      assert.ok(result.layout.second.right <= viewport.width, 'Italic text within viewport');
      assert.ok(result.layout.second.top - result.layout.first.bottom < 1, 'No added line gap');
      const italicFontSize = await page.locator('h1>em').evaluate(e=>parseFloat(getComputedStyle(e).fontSize));
      assert.ok(result.layout.second.height < italicFontSize * 1.3, 'Italic phrase stays on one line');
      assert.deepEqual(result.layout.brokenImages, []);
      await page.screenshot({path:`${output}/home-${viewport.width}.png`});
      if(viewport.width === 1672 || viewport.width === 390) await page.screenshot({path:`${output}/home-${viewport.width}-full.png`,fullPage:true});

      const primary = page.locator('.hero-actions').getByRole('link',{name:'Get started'});
      const secondary = page.locator('.hero-actions').getByRole('link',{name:'Sign in',exact:true});
      await primary.focus();
      assert.equal(await primary.evaluate(e=>e.matches(':focus-visible')),true);
      assert.equal(await primary.evaluate(e=>getComputedStyle(e).outlineStyle),'solid');
      await page.keyboard.press('Tab');
      assert.equal(await secondary.evaluate(e=>e===document.activeElement),true,'Keyboard advances to Sign in');
      await page.keyboard.press('Enter');
      await page.waitForURL('**/login');
      await page.getByRole('heading',{name:'Welcome back.'}).waitFor();
      await page.goBack();await primary.click();await page.waitForURL('**/register');
      await page.locator('input[name=email]').waitFor();
      await page.goBack();

      if(viewport.width === 1672) {
        await page.getByRole('link',{name:'How it works',exact:true}).click();
        await page.waitForURL('**/#how-it-works');
        await page.getByRole('link',{name:'Help',exact:true}).click();
        await page.waitForURL('**/#support');
        await page.locator('summary').filter({hasText:'Can I use this for diagnosis?'}).click();
        assert.equal(await page.locator('details').first().getAttribute('open'),'');
        await page.goto('http://127.0.0.1:4180/');
        const cdp = await context.newCDPSession(page);
        await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'},{name:'prefers-reduced-transparency',value:'reduce'}]});
        assert.equal(await page.evaluate(()=>matchMedia('(prefers-reduced-transparency: reduce)').matches),true);
        assert.equal(await page.locator('.public-nav').evaluate(e=>getComputedStyle(e).backgroundColor),'rgba(0, 0, 0, 0)');
        assert.equal(await primary.evaluate(e=>getComputedStyle(e).backdropFilter),'none');
        await page.screenshot({path:`${output}/home-reduced-transparency.png`});
      }
      assert.deepEqual(errors, []);
    } catch(error) { result.status = 'FAIL'; result.error = error.message; process.exitCode = 1; }
    results.push(result); console.log(viewport.width,result.status,result.error || '');
    await context.close();
  }
} finally {
  await writeFile(`${output}/results.json`, JSON.stringify({browser:await browser.version(),conditions:'Local Chrome headless, DPR 1, emulated viewport sizes; static/reduced-motion screenshots, visual inspection separate',results},null,2));
  await browser.close();
}

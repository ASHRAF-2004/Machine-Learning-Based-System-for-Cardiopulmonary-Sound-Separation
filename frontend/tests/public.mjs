import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(root, process.env.EVIDENCE_ROOT || 'evidence', 'public');
await fs.mkdir(output, {recursive:true});
const browser = await chromium.launch({executablePath:process.env.CHROME_BIN || '/usr/bin/google-chrome', headless:true, args:['--no-sandbox', '--disable-dev-shm-usage']});
const context = await browser.newContext({viewport:{width:1440,height:1000}, reducedMotion:'reduce'});
const page = await context.newPage();
const base = process.env.FRONTEND_URL || 'http://127.0.0.1:4180';
const results = [], errors = [], requests = [];
page.on('pageerror', error => errors.push(error.message));
page.on('request', request => requests.push({url:request.url(), method:request.method()}));
async function test(name, fn) {
  try { await fn(); results.push({name,status:'PASS'}); console.log(`PASS ${name}`); }
  catch (error) {results.push({name,status:'FAIL',error:error.message}); console.error(`FAIL ${name}: ${error.message}`);}
}
async function go(route) { await page.goto(base + route, {waitUntil:'networkidle'}); await page.locator('h1').first().waitFor(); }
async function shot(name, fullPage=false) { await page.screenshot({path:path.join(output,name+'.png'),fullPage}); }
async function textIncludes(value) {assert.ok((await page.locator('body').innerText()).includes(value), `Missing text: ${value}`);}
async function hasNoStored(value) {assert.equal(await page.evaluate(v => JSON.stringify({...localStorage,...sessionStorage}).includes(v),value),false);}

await test('Welcome copy, primary routes and original assets', async()=>{
  await go('/'); await textIncludes('signals within.');
  assert.equal(await page.getByRole('link',{name:/Get started/}).first().getAttribute('href'),'/register');
  assert.ok(await page.locator('img[src="/assets/logo.svg"]').count());
  assert.ok(await page.locator('.owl-art img').evaluate(img=>img.complete && img.naturalWidth>0));
  await shot('welcome-desktop'); await shot('welcome-full',true);
});
await test('Login validation, show/hide, unavailable auth and secret disposal', async()=>{
  await go('/login'); await shot('login-desktop');
  await page.getByRole('button',{name:'Sign in',exact:true}).click(); await textIncludes('Enter a valid email address.');
  await page.locator('input[name="email"]').fill('fictional-auth-check@example.test');
  await page.getByLabel('Password',{exact:true}).fill('DEMO-secret-sentinel-528');
  await page.getByRole('button',{name:'Show password',exact:true}).click();
  assert.equal(await page.getByLabel('Password',{exact:true}).getAttribute('type'),'text');
  await page.getByRole('button',{name:'Hide password',exact:true}).click();
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.getByText(/Live sign-in is not connected/).waitFor();
  assert.equal(await page.getByLabel('Password',{exact:true}).inputValue(),'');
  await hasNoStored('DEMO-secret-sentinel-528'); await hasNoStored('fictional-auth-check@example.test');
});
await test('Registration validates without role input, account creation or password persistence', async()=>{
  await go('/register'); await shot('register-desktop');
  assert.equal(await page.locator('select[name="role"],input[name="role"]').count(),0);
  await page.getByRole('button',{name:'Create account',exact:true}).click(); await textIncludes('Enter your name.');
  await page.locator('input[name="name"]').fill('Fictional Registration Check');
  await page.locator('input[name="email"]').fill('registration-check@example.test');
  await page.getByLabel('Password',{exact:true}).fill('DEMO-registration-1298');
  await page.getByLabel('Confirm password',{exact:true}).fill('mismatch');
  await page.getByRole('button',{name:'Create account',exact:true}).click(); await textIncludes('Passwords must match.');
  await page.getByLabel('Confirm password',{exact:true}).fill('DEMO-registration-1298');
  await page.getByRole('checkbox').check();
  await page.getByRole('button',{name:'Create account',exact:true}).click();
  await page.getByText('Demo registration preview',{exact:true}).waitFor();
  await textIncludes('No real account was created'); await hasNoStored('DEMO-registration-1298'); await hasNoStored('Fictional Registration Check');
});
await test('Password recovery generic acknowledgment and resend cooldown', async()=>{
  await go('/forgot-password'); await page.getByRole('button',{name:'Request reset link',exact:true}).click(); await textIncludes('Enter a valid email address.');
  await page.locator('input[name="email"]').fill('unknown-demo-address@example.test');
  await page.getByRole('button',{name:'Request reset link',exact:true}).click();
  await page.getByText('Request acknowledgment preview',{exact:true}).waitFor();
  await textIncludes('No account lookup was performed.'); await textIncludes('Demo: no email was sent.');
  assert.equal(await page.getByRole('button',{name:/Try again in/}).isDisabled(),true);
  await hasNoStored('unknown-demo-address@example.test');
});
await test('Reset mismatch validation and honest success', async()=>{
  await go('/reset-password?state=valid'); await shot('reset-valid');
  await page.getByLabel('New password',{exact:true}).fill('DEMO-reset-secret-9728');
  await page.getByLabel('Confirm new password',{exact:true}).fill('not-matching');
  await page.getByRole('button',{name:'Reset password',exact:true}).click(); await textIncludes('Passwords must match.');
  await page.getByLabel('Confirm new password',{exact:true}).fill('DEMO-reset-secret-9728');
  await page.getByRole('button',{name:'Reset password',exact:true}).click();
  await page.getByText('Demo: password reset preview complete',{exact:true}).waitFor();
  await hasNoStored('DEMO-reset-secret-9728'); await shot('reset-success');
});
for (const state of ['expired','invalid','used','failure','success']) await test(`Reset state ${state}`, async()=>{
  await go('/reset-password?state='+state);
  if (['expired','invalid','used'].includes(state)) {assert.equal(await page.locator('input[type="password"]').count(),0);assert.ok(await page.getByRole('link',{name:'Request a new link',exact:true}).count());}
  await shot('reset-'+state);
});
await test('Verification resend cooldown, no account verification side effect', async()=>{
  await go('/verify-email'); const before = await page.evaluate(()=>localStorage.getItem('stethofuse-demo-v1'));
  await page.getByRole('button',{name:'Resend verification email',exact:true}).click();
  await page.getByText('Demo resend requested. No email was sent.',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:/Resend available/}).isDisabled(),true);
  assert.equal(await page.evaluate(()=>localStorage.getItem('stethofuse-demo-v1')),before);
});
for (const state of ['verified','expired','invalid','failure','throttled']) await test(`Verification state ${state}`, async()=>{await go('/verify-email?state='+state);await textIncludes('Demo: no email was sent.');});
await test('Google completing resolves to unavailable, never fake success', async()=>{
  await go('/login'); await page.getByRole('button',{name:'Continue with Google',exact:true}).click();
  await page.getByRole('heading',{name:'Google is not connected.'}).waitFor();
  assert.equal(await page.evaluate(()=>sessionStorage.getItem('stethofuse-demo-persona')),null);
  await shot('google-unavailable');
});
for (const state of ['cancelled','error','link-conflict']) await test(`Google ${state}`,async()=>{await go('/auth/callback?state='+state);await textIncludes('No Google account was contacted or linked.');});
await test('Provider action never renders, persists or forwards raw code', async()=>{
  await go('/auth/action?mode=resetPassword&oobCode=DO_NOT_PERSIST_ACTION_7042&state=expired');
  assert.equal((await page.locator('body').innerText()).includes('DO_NOT_PERSIST_ACTION_7042'),false);
  await hasNoStored('DO_NOT_PERSIST_ACTION_7042');
  await page.getByRole('link',{name:'Open password recovery screen',exact:true}).click();
  assert.equal(new URL(page.url()).pathname,'/reset-password'); assert.equal(page.url().includes('DO_NOT_PERSIST_ACTION_7042'),false);
});
for (const route of ['/account-disabled','/session-expired','/privacy','/terms','/403','/404','/500','/offline','/maintenance','/unknown-route-check']) await test(`Route refresh ${route}`, async()=>{await go(route); const title=await page.locator('h1').innerText();assert.ok(title.length>5);await page.reload({waitUntil:'networkidle'});assert.equal(await page.locator('h1').innerText(),title);});
await test('Invalid external return target is replaced with own dashboard',async()=>{
  await go('/login?returnTo=https%3A%2F%2Fexample.com%2Fprivate#demo-personas');
  await page.getByRole('button',{name:/Amina Rahman/}).click();
  await page.waitForURL('**/app/dashboard');
});
for (const target of ['//example.com','/app//example.com','/app/../login','/app/%5C%5Cexample.com']) await test(`Reject unsafe return ${target}`,async()=>{
  await go('/login?returnTo='+encodeURIComponent(target)+'#demo-personas');
  await page.getByRole('button',{name:/Amina Rahman/}).click();await page.waitForURL('**/app/dashboard');
});
await test('Safe in-app return kept but secret query discarded',async()=>{
  await go('/login?returnTo='+encodeURIComponent('/app/recordings?token=NOT_FOR_REDIRECT_884')+'#demo-personas');
  await page.getByRole('button',{name:/Amina Rahman/}).click();await page.waitForURL('**/app/recordings');assert.equal(page.url().includes('NOT_FOR_REDIRECT_884'),false);
});
for (const width of [390,768,1920]) await test(`Public and auth layouts at ${width}px`,async()=>{
  await page.setViewportSize({width,height:width===390?844:1080});
  for(const route of ['/','/login','/register','/reset-password?state=expired']){await go(route); assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Horizontal overflow on ${route}`);await shot(`${route==='/'?'welcome':route.split('?')[0].slice(1)}-${width}`,width===390);}
});
await test('Keyboard access and reduced motion on public hero',async()=>{
  await page.setViewportSize({width:1440,height:1000}); await go('/'); await page.keyboard.press('Tab');
  assert.notEqual(await page.evaluate(()=>document.activeElement?.tagName),'BODY');
  assert.equal(await page.locator('.snow-drift').evaluate(el=>getComputedStyle(el).display),'none');
  assert.equal(await page.locator('.owl-art.has-frames').count(),0);
});
await test('No runtime exceptions and no credential provider requests',async()=>{
  assert.deepEqual(errors,[]);
  const external=requests.filter(r=>!r.url.startsWith(base)&&!r.url.startsWith('data:')&&!r.url.startsWith('blob:'));
  assert.deepEqual(external,[]);
  assert.equal(requests.some(r=>r.method!=='GET'),false);
});

const report={generatedAt:new Date().toISOString(),browser:await browser.version(),mode:'Headless Chrome, reduced-motion emulation; not a real mobile device',base,results,errors,requestCount:requests.length,pass:results.filter(x=>x.status==='PASS').length,fail:results.filter(x=>x.status==='FAIL').length};
await fs.writeFile(path.join(output,'results.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify({pass:report.pass,fail:report.fail,output}));
await browser.close();
process.exitCode=report.fail?1:0;

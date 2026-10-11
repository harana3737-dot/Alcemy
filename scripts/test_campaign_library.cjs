const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8771';
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});try{
const context=await browser.newContext();const page=await context.newPage(),errors=[];
page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',route=>route.abort());
await page.goto(base+'/'+encodeURIComponent('Для игрока — логи, записки и предыстория.html'));
const items=await page.evaluate(()=>JSON.parse(document.getElementById('data').textContent));
await page.evaluate(()=>{window.copied=[];Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.copied.push(text);}}});});
for(const item of items){await page.locator(`[data-id="${item.id}"] .copy`).click();assert.equal(await page.evaluate(()=>window.copied.at(-1)),item.text,'Копируется только выбранный исходный текст');}
await page.locator('#category').selectOption({label:'Опорные диалоги'});assert.equal(await page.locator('.material:visible').count(),6);
await page.locator('#search').fill('ФРАЗА-КОТОРОЙ-НЕТ-7193');assert.equal(await page.locator('.material:visible').count(),0);
await page.locator('#search').fill('');await page.locator('#category').selectOption('');
await page.evaluate(()=>{Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied');}}});document.execCommand=()=>false;});
await page.locator('.copy').first().click();assert.equal(await page.locator('#manual').inputValue(),items[0].text);assert.equal(await page.locator('#fallback').isVisible(),true);
assert.equal(await page.locator('#manual').evaluate(element=>element.selectionEnd-element.selectionStart),items[0].text.length);
await page.locator('#close').click();
await page.evaluate(()=>{document.execCommand=()=>true;});await page.locator('.copy').first().click();assert.match(await page.locator('#status').innerText(),/Скопировано/);
for(const width of [360,1280]){await page.setViewportSize({width,height:900});await page.locator('.material details').first().locator('summary').click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.locator('.material details').first().locator('summary').click();}
const offline=await browser.newContext({javaScriptEnabled:false});const reader=await offline.newPage();await reader.route('**/*',route=>route.request().url().startsWith(base)?route.continue():route.abort());await reader.goto(base+'/'+encodeURIComponent('Для игрока — логи, записки и предыстория.html'));assert.equal(await reader.locator('.material').count(),items.length);await reader.locator('summary').first().click();assert.equal(await reader.locator('.text').first().isVisible(),true);await offline.close();
assert.deepEqual(errors,[]);await context.close();console.log(`PASS: ${items.length} exact copies, filters, clipboard denial and fallback, mobile/desktop, reading without JavaScript`);
}finally{await browser.close();}})().catch(error=>{console.error(error);process.exitCode=1});

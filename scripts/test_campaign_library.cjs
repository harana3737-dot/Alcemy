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
await page.locator('#search').fill('веревку');await page.waitForTimeout(300);const warm=await page.locator('.material:visible').count();assert.ok(warm>0,'ё и е не различаются');
assert.equal(await page.locator('.material:visible details[open]').count(),warm,'найденные карточки раскрыты');assert.ok(await page.locator('.material:visible .text mark').count()>0,'совпадения подсвечены');assert.match(await page.locator('.material:visible .hits').first().innerText(),/Совпадений в тексте: \d+/);
await page.locator('#search').fill('');await page.waitForTimeout(300);assert.equal(await page.locator('.material details[open]').count(),0,'после очистки поиска карточки свёрнуты');assert.equal(await page.locator('.text mark').count(),0);
await page.locator('#category').selectOption({label:'— Дело связки Маррена Вельда'});const velds=items.filter(item=>item.context==='Дело связки Маррена Вельда');assert.equal(await page.locator('.material:visible').count(),velds.length);
await page.locator('#copyAll').click();assert.equal(await page.evaluate(()=>window.copied.at(-1)),velds.map(item=>item.text.replace(/\s+$/,'')).join('\n\n')+'\n');await page.locator('#category').selectOption('');
const s13=items.find(item=>item.label==='S13');await page.locator(`[data-id="${s13.id}"] .link`).click();assert.match(await page.evaluate(()=>window.copied.at(-1)),/#S13$/);
const first=page.locator(`[data-id="${items[0].id}"] .copy`);await first.click();assert.equal(await first.innerText(),'Скопировано');await page.waitForTimeout(2300);assert.equal(await first.innerText(),'Скопировать');
const linked=await context.newPage();await linked.route('https://**/*',route=>route.abort());await linked.goto(base+'/'+encodeURIComponent('Для игрока — логи, записки и предыстория.html')+'#'+encodeURIComponent('ДМ8'));const target=items.find(item=>item.label==='ДМ8');
assert.equal(await linked.locator(`[data-id="${target.id}"] details`).evaluate(element=>element.open),true);assert.equal(await linked.locator(`[data-id="${target.id}"]`).evaluate(element=>element.classList.contains('target')),true);await linked.close();
await page.evaluate(()=>{Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied');}}});document.execCommand=()=>false;});
await page.locator('.copy').first().click();assert.equal(await page.locator('#manual').inputValue(),items[0].text);assert.equal(await page.locator('#fallback').isVisible(),true);
assert.equal(await page.locator('#manual').evaluate(element=>element.selectionEnd-element.selectionStart),items[0].text.length);
await page.locator('#close').click();
await page.evaluate(()=>{document.execCommand=()=>true;});await page.locator('.copy').first().click();assert.match(await page.locator('#status').innerText(),/Скопировано/);
for(const width of [360,1280]){await page.setViewportSize({width,height:900});if(width===360){const [field,select]=await Promise.all(['#search','#category'].map(selector=>page.locator(selector).evaluate(element=>element.getBoundingClientRect().width)));assert.equal(Math.round(field),Math.round(select),'на телефоне список во всю ширину');}await page.locator('.material details').first().locator('summary').click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.locator('.material details').first().locator('summary').click();}
const offline=await browser.newContext({javaScriptEnabled:false});const reader=await offline.newPage();await reader.route('**/*',route=>route.request().url().startsWith(base)?route.continue():route.abort());await reader.goto(base+'/'+encodeURIComponent('Для игрока — логи, записки и предыстория.html'));assert.equal(await reader.locator('.material').count(),items.length);await reader.locator('summary').first().click();assert.equal(await reader.locator('.text').first().isVisible(),true);await offline.close();
assert.deepEqual(errors,[]);await context.close();console.log(`PASS: ${items.length} exact copies, filters, search highlight, links, copy all, clipboard denial and fallback, mobile/desktop, reading without JavaScript`);
}finally{await browser.close();}})().catch(error=>{console.error(error);process.exitCode=1});

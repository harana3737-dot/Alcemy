// Границы страницы, различение примера и мобильное размещение боя.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
const shots=process.env.TABLE_TOOLS_SCREENSHOTS;
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/opt/pw-browsers/chromium',headless:true,args:['--no-sandbox']});
  try{for(const width of [390,1280]){
    const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
    await page.route('https://**/*',r=>r.fulfill({status:200,body:''}));await page.route('**/favicon.ico',r=>r.fulfill({status:204,body:''}));
    const fits=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width,'Страница выходит за границы '+width);
    await page.goto(base+'/'+encodeURIComponent('Помощник варки.html'));await page.waitForFunction(()=>JDB&&ST.mat);
    await fits();await page.locator('[data-tab="smith"]').click();
    const smith=page.locator('#craft-smith');
    assert.equal(await smith.locator('#o-p').innerText(),'0/100');assert.match(await smith.locator('#o-left').innerText(),/подходов нет/);
    await smith.locator('#sample').click();
    assert.equal(await smith.locator('#sample-banner').isVisible(),true);
    assert.match(await smith.locator('#o-p').innerText(),/пример/);
    const banner=await smith.locator('#sample-banner').boundingBox(),tiles=await smith.locator('.out').boundingBox();
    assert.ok(banner.y+banner.height<=tiles.y,'Плашка должна быть над плитками');
    assert.equal(await smith.locator('#log').evaluate(el=>el.parentElement.scrollWidth<=el.parentElement.clientWidth),true,'Журнал кузни не должен прокручиваться по горизонтали');
    await fits();
    if(shots){fs.mkdirSync(shots,{recursive:true});await smith.locator('.calc').screenshot({path:path.join(shots,`smith-${width}.png`)});}
    // Отказ очищать пример оставляет его нетронутым.
    page.once('dialog',d=>d.dismiss());await smith.locator('#d20').fill('10');await smith.locator('#add').click();
    assert.equal(await smith.locator('#sample-banner').isVisible(),true);assert.equal(await smith.locator('#log tbody tr').count(),4);
    await page.reload();await page.locator('[data-tab="smith"]').click();assert.equal(await smith.locator('#sample-banner').isVisible(),true);
    await page.locator('[data-tab="belt"]').click();await page.locator('#fStart').click();
    const head=page.locator('body > .wrap > header');
    if(width===390){
      assert.equal(await page.locator('#headerDetails').isVisible(),false);
      const fight=await page.locator('#fight').boundingBox(),clock=await page.locator('#tab-belt .clock').boundingBox();assert.ok(fight.y<clock.y);
      assert.ok((await head.boundingBox()).height<60,'Шапка боя должна занимать одну строку');
      await page.evaluate(()=>window.scrollTo(0,700));assert.equal(Math.round((await page.locator('nav.tabs').boundingBox()).y),0);
      await page.locator('#mobileTools').click();assert.equal(await page.locator('#backupExport').isVisible(),true);
      await page.locator('#mobileTools').click();
    }else{
      assert.equal(await page.locator('#headerDetails').isVisible(),true);assert.equal(await page.locator('#mobileTools').isVisible(),false);
      const fight=await page.locator('#fight').boundingBox(),clock=await page.locator('#tab-belt .clock').boundingBox();assert.ok(clock.y<fight.y);
    }
    await page.evaluate(()=>window.scrollTo(0,0));await fits();
    if(shots)await page.screenshot({path:path.join(shots,`battle-${width}.png`)});
    // Не переносить режим мобильной шапки на другие вкладки.
    await page.locator('[data-tab="brew"]').click();assert.equal(await page.locator('#headerDetails').isVisible(),true);await fits();
    await page.goto(base+'/'+encodeURIComponent('Пульт мастера.html'));await fits();
    if(shots)await page.screenshot({path:path.join(shots,`master-${width}.png`)});
    assert.deepEqual(errors,[]);await context.close();
  }console.log('PASS: 390/1280, пустая кузня, пример и отказ очищать, журнал без прокрутки, компактная шапка, закреплённые вкладки, границы страницы');}
  finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

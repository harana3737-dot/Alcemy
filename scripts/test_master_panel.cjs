// Ответы мастера, ремёсла и мобильные размеры: отдельно от сумки игрока.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  try {
    const context=await browser.newContext(),page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',r=>r.abort());
    await page.goto(base+'/'+encodeURIComponent('Пульт мастера.html'));
    assert.equal(await page.locator('#qs .q').count(),6);
    assert.equal(await page.locator('#sumN').innerText(),'0 из 6');
    assert.match(await page.evaluate(()=>answerText()),/без нового ответа 6/);
    assert.doesNotMatch(await page.evaluate(()=>answerText()),/молчание — принято|Остальные 6 пунктов — принято/);
    await page.evaluate(()=>localStorage.setItem('manswers',JSON.stringify({q3:{c:'ok',note:'Прежний ответ'}})));
    await page.reload();
    assert.equal(await page.locator('#sumN').innerText(),'0 из 6','Прежний ответ не закрывает новое уточнение');
    assert.match(await page.evaluate(()=>localStorage.getItem('manswers')),/Прежний ответ/);
    await page.locator('#qs .q').first().locator('[data-c="talk"]').click();
    const note=page.locator('#qs .q textarea').first();await note.fill('Проверить | пример\nбез HTML');await note.dispatchEvent('change');
    assert.equal(await page.locator('#sumN').innerText(),'1 из 6');
    await page.locator('[data-all]').first().click();
    assert.equal(await page.locator('#qs [data-c="talk"][aria-pressed="true"]').count(),1,'Групповое принятие сохраняет отдельный ответ');
    await page.reload();assert.equal(await page.locator('#sumN').innerText(),'4 из 6');
    const report=await page.evaluate(()=>answerText());
    assert.match(report,/Проверить \/ пример без HTML/);
    await page.locator('#t-ref').click();
    assert.match(await page.locator('#cout').innerText(),/8\s+предел токсичности/);
    assert.match(await page.locator('#cout').innerText(),/\+5\s+бонус проверки варки/);
    await page.locator('#cin [data-k="help"]').check();
    assert.match(await page.locator('#cout').innerText(),/\+7\s+бонус проверки варки/);
    await page.reload();await page.locator('#t-ref').click();
    assert.equal(await page.locator('#cin [data-k="help"]').isChecked(),true);
    for(const width of [360,1280]){
      await page.setViewportSize({width,height:900});
      await page.locator('#t-scroll').click();
      const scroll=page.locator('#master-scroll');
      assert.equal(await scroll.locator('#o-dc').innerText(),'12');
      await scroll.locator('#lvl').selectOption('1');
      await scroll.locator('#when').selectOption('rush');
      assert.equal(await scroll.locator('#o-dc').innerText(),'17');
      await scroll.locator('#ink').selectOption('2|4');
      assert.equal(await scroll.locator('#o-cost').innerText(),'60 зм');
      await page.locator('#t-smith').click();
      const smith=page.locator('#master-smith');
      assert.equal(await smith.locator('#o-p').innerText(),'0/100');
      await smith.locator('#d20').fill('10');await smith.locator('#add').click();
      assert.equal(await smith.locator('#o-p').innerText(),'21/100');
      await page.reload();
      assert.equal(await page.locator('#p-smith').isVisible(),true,'Вкладка ремесла сохраняется');
      assert.equal(await smith.locator('#o-p').innerText(),'21/100');
      await smith.locator('#reset').click();
      await page.locator('#t-scroll').click();
      assert.equal(await scroll.locator('#when').inputValue(),'rush');
      assert.equal(await scroll.locator('#o-cost').innerText(),'60 зм');
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'Пульт с ремеслом помещается на экран');
      await scroll.locator('#lvl').selectOption('1');await scroll.locator('#when').selectOption('2h');
    }
    assert.deepEqual(errors,[]);await context.close();
    for(const width of [360,375,390,414,1280]){
      const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage(),errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.route('https://**/*',r=>r.abort());
      const fits=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width);
    await page.goto(base+'/'+encodeURIComponent('Пульт мастера.html'));await fits();
    // В CI резервный DejaVu Sans шире локального системного шрифта.
    await page.locator('body').evaluate(el=>el.style.fontFamily='"DejaVu Sans", sans-serif');await fits();
    assert.match(await page.locator('#buildInfo summary').innerText(),/^Сборка [0-9a-f]{12}$/);
    assert.equal(await page.locator('#sumN').innerText(),'0 из 6');
    assert.match(await page.locator('.sum').innerText(),/Неотмеченные пункты остаются без нового ответа/);
    for(const tab of ['ref','el','ta','ok']){
      await page.locator(`[data-t="${tab}"]`).click();await fits();
      if(tab==='el'){
        await page.locator('.el>button').evaluateAll(buttons=>buttons.forEach(button=>button.click()));await fits();
      }
      if(tab==='ref'){
        assert.ok(await page.locator('#p-ref details').count()>0);
        await page.locator('#p-ref details').evaluateAll(items=>items.forEach(item=>item.open=true));await fits();
      }
    }
      assert.deepEqual(errors,[]);await context.close();
    }
    console.log('PASS: ответы мастера, сохранения, ремёсла, мобильные размеры');
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

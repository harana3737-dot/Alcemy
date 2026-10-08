// Регрессии новых ремесленных вкладок и локальных ответов мастера.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||['/usr/bin/chromium','/opt/pw-browsers/chromium'].find(f=>fs.existsSync(f)),headless:true,args:['--no-sandbox']});
  try {
    for(const embedded of [false,true]){
      const context=await browser.newContext();
      const page=await context.newPage(),errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.route('https://**/*',r=>r.abort());
      await page.goto(base+'/'+encodeURIComponent(embedded?'Помощник варки.html':'Шпаргалка кузнеца.html'));
      const smith=embedded?page.locator('#craft-smith'):page;
      if(embedded)await page.locator('[data-tab="smith"]').click();
      assert.equal(await smith.locator('#log caption').count(),1);
      await page.reload();
      if(embedded)await page.locator('[data-tab="smith"]').click();
      assert.equal(await smith.locator('#log caption').count(),1,'Перезагрузка должна сохранить пометку примера');
      await smith.locator('#undo').click();
      assert.equal(await smith.locator('#log caption').count(),1,'Отмена демонстрационного подхода сохраняет пометку примера');
      await smith.locator('#d20').fill('10');await smith.locator('#add').click();
      assert.equal(await smith.locator('#log tbody tr').count(),1,'Первый реальный подход заменяет пример');
      assert.equal(await smith.locator('#o-p').innerText(),'20/100');
      const first=await smith.locator('#log tbody tr').first().innerText();
      await smith.locator('#abk').selectOption('dex');
      await smith.locator('#dc').fill('25');
      assert.equal(await smith.locator('#log tbody tr').first().innerText(),first,'Новые условия не меняют выполненный подход');
      await smith.locator('#d20').fill('10');await smith.locator('#add').click();
      assert.match(await smith.locator('#log tbody tr').nth(1).innerText(),/провал на 5/);
      assert.equal(await smith.locator('#o-p').innerText(),'20/100');
      await page.reload();
      if(embedded)await page.locator('[data-tab="smith"]').click();
      assert.equal(await smith.locator('#log tbody tr').first().innerText(),first);
      await smith.locator('#undo').click();
      assert.equal(await smith.locator('#o-mk').innerText(),'1 / 0 / 0');
      await smith.locator('#d20').fill('1');
      await smith.locator('#sub').fill('20');await smith.locator('#add').click();
      assert.equal(await smith.locator('#o-p').innerText(),'0/100');
      await smith.locator('#reset').click();
      assert.equal(await smith.locator('#o-p').innerText(),'0/100');
      // Старый формат журнала мигрирует один раз, сохраняя броски и исходные настройки.
      await page.evaluate(()=>localStorage.setItem('smith-log-5',JSON.stringify({rolls:[{d:10}],ab:4,pb:2,ml:2,ws:3,dc:14,vol:100})));
      await page.reload();
      if(embedded)await page.locator('[data-tab="smith"]').click();
      assert.equal(await smith.locator('#o-p').innerText(),'20/100');
      await smith.locator('#ws').selectOption('0');
      assert.equal(await smith.locator('#o-p').innerText(),'20/100');
      assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('smith-log-5')).rolls[0].b),10);
      if(embedded){
        await page.locator('[data-tab="scroll"]').click();
        const scroll=page.locator('#craft-scroll');
        await scroll.locator('#when').selectOption('short');
        assert.equal(await scroll.locator('#o-dc').innerText(),'15');
        await scroll.locator('#when').selectOption('rush');
        assert.equal(await scroll.locator('#o-dc').innerText(),'17');
        await scroll.locator('#ink').selectOption('2|4');
        assert.equal(await scroll.locator('#o-cost').innerText(),'60 зм');
        await page.waitForFunction(()=>JDB&&ST.mat);
        const catalog=await page.evaluate(()=>{
          const c=D.find(c=>c.n==='Левитация'),p=D.find(c=>c.k==='eff'&&c.l===2);
          const known=brew(p,2,4,{}),unknown=brew(p,2,4,{first:true});
          return {count:D.length,poisons:D.filter(c=>c.k==='psn').length,tox:c.t,a89:c.a,dcDifference:unknown.dc-known.dc,batch:unknown.n,knownBatch:known.n};
        });
        assert.equal(catalog.count,184);assert.equal(catalog.poisons,12);
        assert.match(catalog.tox,/^1\b/);assert.equal(catalog.a89,false);
        assert.equal(catalog.dcDifference,2);assert.equal(catalog.batch,1);assert.equal(catalog.knownBatch,2);
        const lss=await page.evaluate(()=>{
          const old=ST.bag;try{ST.bag=[{n:'Подмога',q:2,who:'p1',note:'Длительность ×2'},
            {n:'Подмога (нестабильное)',q:1,who:'p1',note:'дефект: ещё не назначен'},
            {n:'Сопротивление',q:1,who:'p1',note:'на разборку'}];return lssBlocks().find(b=>b.t.startsWith('Снаряжение: подразделы')).x;
          }finally{ST.bag=old}
        });
        assert.match(lss,/Подмога ×2 \(Длительность ×2\)/);
        assert.match(lss,/Подмога \(нестабильное\) \(дефект: ещё не назначен\)/);
        assert.match(lss,/На разборку\nСопротивление/);
        // Ж-105: успешные эликсиры разных классов пополняют мастерство.
        for(const kind of ['eff','chg','fl']){
          const track=await page.evaluate(kind=>{
            const c=D.find(c=>c.k===kind&&c.l===2);if(!c)throw Error('Нет карточки класса '+kind);
            document.getElementById('m').value='2';const box=document.createElement('div');box.id='review-brew';
            document.body.appendChild(box);recForm(box,{name:c.n,card:c,noUse:true});return 'mastery-2-3';
          },kind);
          const old=await page.evaluate(id=>TR.find(t=>t.id===id)?.current||0,track);
          await page.locator('#review-brew [data-k="ok"]').fill('1');
          await page.locator('#review-brew .rgo').click();
          await page.waitForFunction(({id,old})=>TR.find(t=>t.id===id)?.current===old+1,{id:track,old});
          await page.evaluate(()=>document.getElementById('review-brew').remove());
        }
        await page.reload();await page.locator('[data-tab="scroll"]').click();
        assert.equal(await scroll.locator('#when').inputValue(),'rush');
        assert.equal(await scroll.locator('#o-cost').innerText(),'60 зм');
      }
      assert.deepEqual(errors,[]);await context.close();
    }
    const context=await browser.newContext(),page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',r=>r.abort());
    await page.goto(base+'/'+encodeURIComponent('Пульт мастера.html'));
    assert.equal(await page.locator('#qs .q').count(),42);
    await page.locator('#qs .q').first().locator('[data-c="talk"]').click();
    const note=page.locator('#qs .q textarea').first();await note.fill('Проверить | пример\nбез HTML');await note.dispatchEvent('change');
    assert.equal(await page.locator('#sumN').innerText(),'41 из 42');
    await page.locator('[data-all]').first().click();
    assert.equal(await page.locator('#qs [data-c="talk"][aria-pressed="true"]').count(),1,'Групповое принятие сохраняет отдельный ответ');
    await page.reload();assert.equal(await page.locator('#sumN').innerText(),'41 из 42');
    const report=await page.evaluate(()=>answerText());
    assert.match(report,/Проверить \/ пример без HTML/);
    await page.locator('#t-ref').click();
    assert.match(await page.locator('#cout').innerText(),/7\s+предел токсичности/);
    assert.match(await page.locator('#cout').innerText(),/\+4\s+бонус проверки варки/);
    await page.locator('#cin [data-k="help"]').check();
    assert.match(await page.locator('#cout').innerText(),/\+6\s+бонус проверки варки/);
    await page.reload();await page.locator('#t-ref').click();
    assert.equal(await page.locator('#cin [data-k="help"]').isChecked(),true);
    assert.deepEqual(errors,[]);await context.close();
    console.log('OK: кузня отдельно и во вкладке, сохранения/миграция/история, свитки, пульт мастера');
  } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

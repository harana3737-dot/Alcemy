// Сочетания, сохранение плана, скрытый каталог и переход к долгим варкам.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/opt/pw-browsers/chromium',headless:true,args:['--no-sandbox']});
  try{for(const width of [360,1280]){
    const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.route('https://**/*',r=>r.fulfill({status:200,body:''}));
    await page.goto(base+'/'+encodeURIComponent('Помощник варки.html'));await page.waitForFunction(()=>JDB&&ST.mat);
    const state=await page.evaluate(()=>JSON.stringify(ST));
    // Перерисовка пояса больше не заменяет скрытый каталог, при возврате он обновляется.
    await page.locator('[data-tab="belt"]').click();
    assert.equal(await page.evaluate(()=>{const el=$('avRecipe');renderBelt();return el===$('avRecipe')}),true);
    await page.locator('[data-tab="brew"]').click();
    assert.equal(await page.evaluate(()=>{AV.selected='нет такого рецепта';renderAvailability();return $('avRecipe').value===AV.selected}),true);
    // Два разных вида концентрации совместимы, каждый ограничен отдельно.
    const checks=await page.evaluate(()=>{
      const context={tox:0,limit:7,alchemy:[],concentration:''};
      const plan=names=>names.map(n=>({n,q:1}));
      return {
        separate:checkCombo(plan(['Щит веры','Изгнание']),context),
        alchemy:checkCombo(plan(['Щит веры','Размытый образ']),context),
        normal:checkCombo(plan(['Изгнание','Сглаз']),context),
        current:checkCombo(plan(['Изгнание']),{...context,concentration:'Паутина'}),
        overdose:checkCombo([{n:'Щит веры',q:2}],{...context,tox:6}),
        residual:checkCombo([],{...context,tox:8}),
        duplicate:checkCombo([{n:'Доспехи мага',q:2}],context),
        repeatedCharges:checkCombo(plan(['Психическая плеть','Психическая плеть']),context),
        soft:checkCombo(plan(['Видение невидимого']),context)
      };
    });
    assert.equal(checks.separate.warnings.length,0);
    assert.ok(checks.alchemy.warnings.some(x=>x.startsWith('Алхимическая концентрация')));
    assert.ok(checks.normal.warnings.some(x=>x.startsWith('Обычная концентрация')));
    assert.ok(checks.current.warnings.some(x=>x.includes('Паутина')));
    assert.equal(checks.overdose.excess,1);assert.ok(checks.overdose.warnings.some(x=>x.includes('СЛ 12')));
    assert.ok(checks.residual.warnings.every(x=>!x.includes('спасбросок')));
    assert.ok(checks.duplicate.warnings.some(x=>x.includes('не складываются')));
    assert.equal(checks.repeatedCharges.warnings.length,0);
    assert.equal(checks.soft.added,0);
    const live=await page.evaluate(()=>{
      const before=ST.ent;try{
        const e={who:'p1',n:'Размытый образ',k:'eff',t0:ST.T-120,dur:60,tox:1,a:true};ST.ent=[e];
        const check=()=>checkCombo([{n:'Щит веры',q:1}],{tox:toxOfP('p1'),limit:7,alchemy:ST.ent.filter(x=>x.a&&isActive(x)).map(x=>x.n)});
        const expired=check();e.dur=240;return {expired,active:check()};
      }finally{ST.ent=before}
    });
    assert.equal(live.expired.total,2);assert.equal(live.expired.warnings.length,0);
    assert.equal(live.active.total,2);assert.ok(live.active.warnings.some(x=>x.includes('Размытый образ')));
    // Сам план не расходует сумку, не меняет хиты, токсичность или журнал.
    await page.locator('[data-tab="combo"]').click();
    await page.locator('#comboCatalog').check();await page.locator('#comboAdd').click();
    await page.locator('.combo-name').selectOption('Щит веры');
    assert.match(await page.locator('#comboResult').innerText(),/не хватает/);
    await page.locator('#comboAdd').click();await page.locator('.combo-name').nth(1).selectOption('Размытый образ');
    assert.match(await page.locator('#comboResult').innerText(),/Алхимическая концентрация/);
    assert.equal(await page.evaluate(()=>JSON.stringify(ST)),state);
    await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);
    assert.equal(await page.locator('#tab-combo').isVisible(),true);assert.equal(await page.locator('.combo-name').count(),2);
    assert.equal(await page.locator('.combo-name').first().inputValue(),'Щит веры');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width);
    // Активная варка видна из рецептов, готовая тоже остаётся до завершения.
    await page.evaluate(()=>{ST.vol=[{id:'test-volume',kind:'elixir',n:'Тестовая варка',l:6,dc:19,volume:30,prog:30,marks:0,hitch:0,def:0,t0:ST.T,last:ST.T,log:[]}];tab('brew')});
    assert.match(await page.locator('#activeBrews').innerText(),/готова к завершающей проверке/);
    await page.locator('#openActiveBrews').click();assert.equal(await page.locator('#tab-jour').isVisible(),true);
    await page.evaluate(()=>{ST.vol=[];tab('brew')});assert.equal(await page.locator('#activeBrews').isVisible(),false);
    assert.deepEqual(errors,[]);await context.close();
  }console.log('PASS: сочетания, два вида концентрации, передозировка, дубли, сохранение без расхода, скрытый каталог, долгие варки, 360/1280');}
  finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

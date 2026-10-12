// Ресурсы боя: реальные действия, миграция, обратимые сохранения и границы.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/opt/pw-browsers/chromium',headless:true,args:['--no-sandbox']});
  try{for(const width of [390,1280]){
    const context=await browser.newContext({viewport:{width,height:900},acceptDownloads:true}),page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('Failed to load resource'))errors.push(m.text())});
    await page.route('https://**/*',r=>r.fulfill({status:200,body:''}));
    await page.goto(base+'/'+encodeURIComponent('Помощник варки.html'));
    await page.waitForFunction(()=>JDB&&ST.mat);
    await page.locator('[data-tab="belt"]').click();await page.locator('#fStart').click();
    assert.equal(await page.locator('#fHp').innerText(),'42 / 42');
    const before=await page.evaluate(()=>ST.bag.find(b=>b.who==='p1'&&b.n==='Зелье 3.3').q);
    await page.locator('[data-slot="2"]').click();
    await page.locator('#fConcentration').fill('Паутина');await page.locator('#fConcentration').dispatchEvent('change');
    await page.locator('#fAmount').fill('12');await page.locator('#fDamage').click();
    assert.equal(await page.locator('#fHp').innerText(),'30 / 42');
    assert.match(await page.locator('#fConcentrationDC').innerText(),/СЛ концентрации 10/);
    const potion=page.locator('#bag .bagi').filter({hasText:'Зелье 3.3'});
    await potion.getByRole('button',{name:'Потратить',exact:true}).click();
    assert.match(await page.locator('.fnow').innerText(),/бросить/);
    await page.locator('#fAmount').fill('9');await page.locator('#fHeal').click();
    assert.equal(await page.locator('#fHp').innerText(),'39 / 42');
    await page.locator('#fReaction').click();assert.equal(await page.locator('#fReaction').isDisabled(),true);
    await page.locator('#fTurn').click();assert.equal(await page.locator('#fReaction').isEnabled(),true);
    await page.locator('#fTempAmount').fill('5');await page.locator('#fSetTemp').click();
    page.once('dialog',d=>d.accept());await page.locator('#fWave').click();
    assert.equal(await page.locator('#fHp').innerText(),'42 / 42');
    assert.equal(await page.locator('#fSlot2').innerText(),'3 / 3');
    assert.equal(await page.locator('#fTemp').innerText(),'0');
    assert.equal(await page.evaluate(()=>ST.bag.find(b=>b.who==='p1'&&b.n==='Зелье 3.3').q),before-1);
    assert.match(await page.locator('#tab-belt #log').innerText(),/После долгого отдыха/);
    assert.equal(await page.locator('#fSlot3').innerText(),'2 / 2');
    await page.locator('#fConcentration').fill('Паутина');await page.locator('#fConcentration').dispatchEvent('change');
    await page.locator('#fTempAmount').fill('5');await page.locator('#fSetTemp').click();
    // Концентрация проверяется и при уроне, который полностью съедают временные хиты.
    await page.locator('#fAmount').fill('4');await page.locator('#fDamage').click();
    assert.equal(await page.locator('#fHp').innerText(),'42 / 42');assert.equal(await page.locator('#fTemp').innerText(),'1');
    assert.match(await page.locator('#fConcentrationDC').innerText(),/СЛ концентрации 10/);
    await page.locator('#fAmount').fill('29');await page.locator('#fDamage').click();
    assert.equal(await page.locator('#fHp').innerText(),'14 / 42');assert.match(await page.locator('#fConcentrationDC').innerText(),/СЛ концентрации 14/);
    // Конверсия не расходует ограниченный запас Адепта; созданные ячейки сверх базового запаса разрешены.
    await page.locator('[data-from-sp="2"]').click();
    assert.equal(await page.locator('#fSlot2').innerText(),'4 / 3');assert.equal(await page.locator('#fSp').innerText(),'2 / 5');
    assert.equal(await page.locator('#fMeta').innerText(),'2 / 2');assert.equal(await page.locator('[data-from-sp="2"]').isDisabled(),true);
    await page.locator('[data-to-sp="2"]').click();assert.equal(await page.locator('#fSp').innerText(),'4 / 5');
    assert.equal(await page.locator('[data-to-sp="2"]').isDisabled(),true);
    await page.locator('#fSpAmount').fill('2');await page.locator('#fSpendMeta').click();assert.equal(await page.locator('#fMeta').innerText(),'0 / 2');
    await page.reload();await page.locator('[data-tab="belt"]').click();assert.equal(await page.locator('#fHp').innerText(),'14 / 42');
    // Файл действительно скачивается, затем восстанавливается через интерфейс.
    if(width===390)await page.locator('#mobileTools').click();
    const downloadEvent=page.waitForEvent('download');await page.locator('#backupExport').click();
    const download=await downloadEvent, saved=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
    assert.equal(saved.state.talis.hp,14);assert.equal(saved.state.talis.meta,0);
    await page.locator('#fAmount').fill('99');await page.locator('#fHeal').click();
    await page.locator('#backupFile').setInputFiles({name:'save.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(saved))});
    await page.locator('#restoreApply').click();await page.waitForFunction(()=>ST.talis.hp===14);
    assert.equal(await page.locator('#fHp').innerText(),'14 / 42');
    const corrupt=structuredClone(saved);corrupt.state.talis.sp=6;
    await page.locator('#backupFile').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(corrupt))});
    // setInputFiles завершается раньше асинхронного чтения и проверки JSON.
    await page.waitForFunction(()=>/повреждённый/.test(document.getElementById('backupStatus').textContent));
    assert.match(await page.locator('#backupStatus').innerText(),/повреждённый/);
    assert.equal(await page.locator('#restoreDialog').isVisible(),false);
    await page.evaluate(()=>{ST.talis.sp=5;ST.talis.slots[3]=2;renderBelt()});
    await page.locator('[data-from-sp="3"]').click();
    assert.equal(await page.locator('#fSlot3').innerText(),'3 / 2');
    assert.equal(await page.locator('#fSp').innerText(),'0 / 5');
    await page.locator('[data-to-sp="3"]').click();
    assert.equal(await page.locator('#fSlot3').innerText(),'2 / 2');
    assert.equal(await page.locator('#fSp').innerText(),'3 / 5');
    // Старый файл без полей III круга принимается, недостающие ячейки не восстанавливаются.
    const legacy=structuredClone(saved);delete legacy.state.talis.slots[3];
    await page.locator('#backupFile').setInputFiles({name:'legacy.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(legacy))});
    await page.locator('#restoreApply').click();await page.waitForFunction(()=>ST.talis.hp===14);
    assert.equal(await page.evaluate(()=>ST.talis.slots[3]),0);
    // Старый файл без новых полей получает максимумы нового листа.
    const old=structuredClone(saved);delete old.state.talis;
    await page.locator('#backupFile').setInputFiles({name:'old.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(old))});
    await page.locator('#restoreApply').click();await page.waitForFunction(()=>ST.talis.hp===42);
    assert.equal(await page.locator('#fSlot1').innerText(),'4 / 4');
    assert.deepEqual(errors,[]);await context.close();
  }console.log('PASS: 390/1280, ресурсы, зелье, отдых без возврата расходников, концентрация, реакция, преобразования, сохранения и миграция');}
  finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

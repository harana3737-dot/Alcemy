// Варианты реальных флаконов, метамагия при варке и совместимость старого плана.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/opt/pw-browsers/chromium',headless:true,args:['--no-sandbox']});
  try{for(const width of [360,1280]){
    const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',r=>r.fulfill({status:200,body:''}));
    await page.goto(base+'/'+encodeURIComponent('Помощник варки.html'));await page.waitForFunction(()=>JDB&&ST.mat);
    const rulings=await page.evaluate(()=>{
      const original=ST;
      try{
        const charge=byName('Психическая плеть'),poison=D.find(c=>c.k==='psn');
        const brewPlain=brew(charge,10,4,{}),brewMeta=brew(charge,10,4,{metamagic:true});
        ST=JSON.parse(JSON.stringify(ST));ST.ent=[];ST.rests=[];ST.lrs=[];ST.lrN=null;
        const who=ST.people[0].id;
        // Старые сохранённые триггеры больше не повышают токсичность.
        ST.trig=Array.from({length:10},(_,n)=>({who,T:ST.T,n:n+1}));
        const triggersOnly=toxOfP(who);
        ST.ent.push({who,k:'eff',t0:ST.T,dur:60,tox:2});
        const mixed=toxOfP(who);ST.ent=[];renderPeople();
        const text=document.querySelector('.pcard').textContent;
        return {brewDelta:brewMeta.dc-brewPlain.dc,successDrops:brewMeta.p.ok+brewMeta.p.hi<brewPlain.p.ok+brewPlain.p.hi,
          poisonBrewDelta:brew(poison,10,4,{metamagic:true}).dc-brew(poison,10,4,{}).dc,
          triggersOnly,mixed,text};
      }finally{ST=original;renderBelt();renderPeople()}
    });
    assert.equal(rulings.brewDelta,2);assert.equal(rulings.successDrops,true);assert.equal(rulings.poisonBrewDelta,0);
    assert.equal(rulings.triggersOnly,0);assert.equal(rulings.mixed,2);
    assert.match(rulings.text,/Триггеры зелий: 10, без токсичности/);
    const model=await page.evaluate(()=>{
      const variants=checkCombo([{n:'Бутилированное дыхание',q:1,variant:1,mods:{heavy:true}}],{tox:0,limit:7});
      const long=flaskProfile(byName('Доспехи мага'),{long:true});
      const doubled=flaskProfile(byName('Доспехи мага'),{dbl:true,short:true,clean:true});
      const charge=flaskProfile(byName('Психическая плеть'),{lwin:true,twin:true});
      return {variants,long,doubled,charge,kits:Object.values(COMBO_KITS).flat().every(n=>!!byName(n))};
    });
    assert.equal(model.kits,true);
    assert.equal(model.variants.added,2);assert.equal(model.long.duration,540);assert.equal(model.doubled.duration,480);
    assert.equal(model.doubled.clean,true);assert.equal(model.charge.duration,240);assert.equal(model.charge.uses,2);
    await page.evaluate(()=>localStorage.setItem('tab','brewing-plan'));
    await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);
    assert.equal(await page.locator('#tab-brew').isVisible(),true);
    await page.locator('[data-tab="belt"]').click();
    await page.locator('[data-tab="combo"]').click();await page.locator('#comboKit').selectOption('Защита');
    assert.equal(await page.locator('.combo-name').count(),2);assert.match(await page.locator('#comboResult').innerText(),/не хватает/);
    await page.locator('#comboFilter').selectOption('soft');assert.equal(await page.evaluate(()=>byName($('comboItems').querySelector('select').options[1]?.value)?.t.startsWith('0')),true);
    await page.locator('#comboClear').click();
    await page.evaluate(()=>{ST.bag.push({n:'Доспехи мага',who:'p1',q:1,note:'Долгое действие'},{n:'Доспехи мага',who:'p1',q:4,note:''});COMBO.items=[{n:'Доспехи мага',q:2}];COMBO.filter='';saveCombo()});
    await page.locator('.combo-bottle').selectOption('Долгое действие');
    assert.match(await page.locator('#comboResult').innerText(),/не хватает 1 доз с этой пометкой/);
    assert.equal(await page.locator('[data-mod="long"]').isChecked(),true);
    const duration=await page.evaluate(()=>checkCombo(COMBO.items,{tox:0,limit:7}).rows[0].profile.duration);assert.equal(duration,540);
    await page.locator('[data-mod="dbl"]').check();assert.equal(await page.locator('[data-mod="long"]').isChecked(),false);
    assert.equal(await page.evaluate(()=>COMBO.items[0].note===undefined),true);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width);
    const backup=await page.evaluate(()=>{const saved=snapshot();saved.plans.brewing.progress=15;saved.settings.tab="brewing-plan";validateSnapshot(saved);const legacy=JSON.parse(JSON.stringify(saved));delete legacy.plans;validateSnapshot(legacy);const bad=JSON.parse(JSON.stringify(saved));bad.plans.combo.items[0].mods.long='yes';let rejected=false;try{validateSnapshot(bad)}catch(e){rejected=true}return {saved,rejected}});
    assert.equal(backup.rejected,true);
    await page.evaluate(()=>{COMBO.items=[];saveCombo()});
    await page.locator('#backupFile').setInputFiles({name:'planning.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(backup.saved))});
    await page.locator('#restoreApply').click();await page.waitForFunction(()=>snapshot().plans.brewing.progress===15&&COMBO.items.length===1);
    await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);assert.equal(await page.evaluate(()=>snapshot().plans.brewing.progress),15);
    assert.equal(await page.locator('#tab-brew').isVisible(),true);
    assert.deepEqual(errors,[]);await context.close();
  }console.log('PASS: метамагия при варке, пресеты, варианты и пометки флаконов, старый JSON с планом и восстановление на вкладке варки, 360/1280');}
  finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

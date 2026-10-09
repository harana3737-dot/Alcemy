// Прогноз, ограничения подбора и варианты реальных флаконов.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/opt/pw-browsers/chromium',headless:true,args:['--no-sandbox']});
  try{for(const width of [360,1280]){
    const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',r=>r.fulfill({status:200,body:''}));
    await page.goto(base+'/'+encodeURIComponent('Помощник варки.html'));await page.waitForFunction(()=>JDB&&ST.mat);
    const state=await page.evaluate(()=>JSON.stringify(ST));
    const model=await page.evaluate(()=>{
      const f=masteryForecast(2,4,0,12),finished=masteryForecast(2,4,15,0);
      const one=expectedBatches(1,2,.75),two=expectedBatches(2,2,.75);
      const variants=checkCombo([{n:'Бутилированное дыхание',q:1,variant:1,mods:{heavy:true}}],{tox:0,limit:7});
      const long=flaskProfile(byName('Доспехи мага'),{long:true});
      const doubled=flaskProfile(byName('Доспехи мага'),{dbl:true,short:true,clean:true});
      const charge=flaskProfile(byName('Психическая плеть'),{lwin:true,twin:true});
      // Независимая симуляция объёма работы: ожидаемые часы должны совпадать.
      let seed=1337;const die=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return Math.floor(seed/4294967296*20)+1};
      let total=0;for(let i=0;i<20000;i++){let progress=0,steps=0;while(progress<90){const r=die(),x=r+4;let add=r===1?-die():r===20?2*x:x>=19?x:x>=15?Math.floor(x/2):0;progress=Math.max(0,progress+add);steps++;if(steps>10000)throw Error('simulation stuck')}total+=steps*2}
      return {f,finished,one,two,variants,long,doubled,charge,highest:masteryForecast(10,4,0,12),volume:volumeHours(6,19,4),simulated:total/20000,kits:Object.values(COMBO_KITS).flat().every(n=>!!byName(n))};
    });
    assert.equal(model.kits,true);assert.equal(model.f.success,.75);assert.equal(model.f.size,2);assert.equal(model.f.dc,10);
    assert.equal(model.finished.hours,0);assert.equal(model.finished.gold,0);assert.equal(model.finished.weeks,null);assert.equal(model.highest,null);
    assert.ok(Math.abs(model.one-1/.9375)<1e-10);assert.ok(Math.abs(model.two-(1+.35/.9375)/.9375)<1e-10);
    assert.ok(model.f.attempts>15/.8,'Последняя полная партия учитывает избыток прогресса');
    assert.equal(model.variants.added,1);assert.equal(model.long.duration,540);assert.equal(model.doubled.duration,480);
    assert.equal(model.doubled.clean,true);assert.equal(model.charge.duration,240);assert.equal(model.charge.uses,2);
    assert.ok(Math.abs(model.volume-model.simulated)<model.volume*.04,JSON.stringify({volume:model.volume,simulation:model.simulated}));
    const picks=await page.evaluate(()=>{
      const original=ST,mastery=$('m').value,lab=S.t.lab,ess=S.t.ess;
      try{
        ST=JSON.parse(JSON.stringify(ST));ST.knownRecipes=['Зелье лечения 1.1','Зелье лечения 2.2'];ST.mat={herbs:[],ess:[],cat:[],other:[],pools:[],gold:0};$('m').value=2;S.t.lab=false;S.t.ess=false;
        const cfg={budget:.1,hours:2,need:'Лечение'};
        const affordable=recommendBrews(cfg).map(r=>r.c.n),noTime=recommendBrews({...cfg,hours:1}),stockOnly=recommendBrews({...cfg,stockOnly:true});
        ST.mat.herbs=[{k:'heal',l:2,q:2}];
        const growth=recommendBrews({...cfg,budget:0,need:'Рост мастерства'}).map(r=>r.c.n);
        ST.knownRecipes.push(recipeKey(byName('Каменная кожа')));$('m').value=5;
        const component=recommendBrews({budget:99,hours:4,need:'Защита',search:'Каменная кожа'});
        $('m').value=2;const above=recommendBrews({budget:10000,hours:100,need:'Защита',search:'Каменная кожа'});
        return {affordable,noTime:!!noTime.length,stockOnly:!!stockOnly.length,growth,component:!!component.length,above:!!above.length};
      }finally{ST=original;$('m').value=mastery;S.t.lab=lab;S.t.ess=ess}
    });
    assert.deepEqual(picks.affordable,['Зелье лечения 1.1']);assert.equal(picks.noTime,false);assert.equal(picks.stockOnly,false);
    assert.deepEqual(picks.growth,['Зелье лечения 2.2']);assert.equal(picks.component,false);assert.equal(picks.above,false);
    await page.locator('[data-tab="brewing-plan"]').click();assert.match(await page.locator('#bpForecast').innerText(),/19,33/);
    await page.locator('#bpProgress').fill('15');await page.locator('#bpProgress').dispatchEvent('change');assert.match(await page.locator('#bpForecast').innerText(),/0 ч/);
    await page.locator('#bpBudget').fill('0');await page.locator('#bpBudget').dispatchEvent('change');
    assert.equal(await page.evaluate(()=>JSON.stringify(ST)),state);await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);
    assert.equal(await page.locator('#tab-brewing-plan').isVisible(),true);assert.equal(await page.locator('#bpProgress').inputValue(),'15');
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
    const backup=await page.evaluate(()=>{const saved=snapshot();validateSnapshot(saved);const legacy=JSON.parse(JSON.stringify(saved));delete legacy.plans;validateSnapshot(legacy);const bad=JSON.parse(JSON.stringify(saved));bad.plans.combo.items[0].mods.long='yes';let rejected=false;try{validateSnapshot(bad)}catch(e){rejected=true}return {saved,rejected}});
    assert.equal(backup.rejected,true);
    await page.evaluate(()=>{COMBO.items=[];BP.progress=1;saveCombo();saveBrewingPlan()});
    await page.locator('#backupFile').setInputFiles({name:'planning.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(backup.saved))});
    await page.locator('#restoreApply').click();await page.waitForFunction(()=>BP.progress===15&&COMBO.items.length===1);
    await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);assert.equal(await page.evaluate(()=>BP.progress),15);
    assert.deepEqual(errors,[]);await context.close();
  }console.log('PASS: прогноз партий, нат. 20, объём VI+, бюджет, время, материалы, мастерство, пресеты, варианты и пометки флаконов, 360/1280');}
  finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

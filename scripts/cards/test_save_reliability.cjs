// Реальные отказы localStorage, перенос ремёсел и безопасный вывод импортированного боя.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const contexts=[];
 async function open(){
  const context=await browser.newContext({viewport:{width:390,height:844}});contexts.push(context);
  const page=await context.newPage();page.errors=[];page.on('pageerror',e=>page.errors.push(e.message));
  await page.route('https://**/*',r=>r.abort());await page.goto(base+'/'+encodeURIComponent('Помощник варки.html'));
  await page.waitForFunction(()=>JDB&&ST.mat);return page;
 }
 async function load(page,data){
  await page.locator('#backupFile').setInputFiles({name:'test-save.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});
  await page.locator('#restoreDialog').waitFor({state:'visible'});
 }
 async function restore(page,data){await load(page,data);await page.locator('#restoreApply').click();await page.locator('#restoreDialog').waitFor({state:'hidden'})}
 async function failWrites(page,key,once=false){
  await page.evaluate(({key,once})=>{window.originalSetItem=Storage.prototype.setItem;let failed=false;
   Storage.prototype.setItem=function(k,v){if(k===key&&(!once||!failed)){failed=true;throw new DOMException('Проверочный отказ','QuotaExceededError')}return window.originalSetItem.call(this,k,v)};
  },{key,once});
 }
 async function allowWrites(page){await page.evaluate(()=>{Storage.prototype.setItem=window.originalSetItem})}
 try{
  const page=await open();
  await page.evaluate(async()=>{await JDB.collection('tracks').doc('quota-test').set({name:'Проверка',group:'project',target:10,current:1,log:[]})});
  await failWrites(page,'tracks');
  const quota=await page.evaluate(async()=>({ok:await jUpdate('quota-test',{current:2}),current:TR.find(t=>t.id==='quota-test').current,status:$('jstat').textContent}));
  assert.equal(quota.ok,false);assert.equal(quota.current,1);assert.match(quota.status,/Не сохранено.*переполнено/);
  const ghost=await page.evaluate(async()=>{mutate(()=>logx('проверка отмены'));const ok=await jAdd(TR.find(t=>t.id==='quota-test'),1,'проверка');return {ok,ghost:Object.values(UNDOJ).flat().some(x=>x.id==='quota-test')}});
  assert.deepEqual(ghost,{ok:false,ghost:false});await allowWrites(page);
  const oldGold=await page.evaluate(()=>JSON.parse(localStorage.getItem('belt')).mat.gold);
  await failWrites(page,'belt');
  await page.evaluate(()=>mutate(()=>{ST.mat.gold=12.34}));
  assert.match(await page.locator('#savest').innerText(),/Не сохранено в браузере/);
  assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('belt')).mat.gold),oldGold);
  // Отказ обоих способов хранения не должен обещать локальную копию.
  await page.evaluate(()=>{DOC={set:async()=>{throw Error('Нет связи')}};save()});
  await page.waitForFunction(()=>$('savest').textContent.includes('ни в аккаунте, ни в браузере'));
  await page.evaluate(()=>{DOC={set:async()=>{}};save()});
  await page.waitForFunction(()=>$('savest').textContent.includes('Сохранено в аккаунте; в браузере не сохранилось'));
  await page.evaluate(()=>{DOC=null});await allowWrites(page);
  await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);
  assert.equal(await page.evaluate(()=>ST.mat.gold),oldGold);
  assert.equal(await page.evaluate(()=>TR.find(t=>t.id==='quota-test').current),1);
  // Заполняем ремёсла через настоящие формы и скачиваем общий JSON.
  await page.locator('[data-tab="smith"]').click();const smith=page.locator('#craft-smith');
  await smith.locator('#d20').fill('10');await smith.locator('#add').click();
  const progress=await smith.locator('#o-p').innerText();assert.equal(progress,'21/100');
  await page.locator('[data-tab="scroll"]').click();const scroll=page.locator('#craft-scroll');
  await scroll.locator('#when').selectOption('rush');await scroll.locator('#ink').selectOption('2|4');
  const downloaded=page.waitForEvent('download');await page.locator('#backupExport').click();
  const save=JSON.parse(fs.readFileSync(await (await downloaded).path(),'utf8'));
  assert.equal(save.crafts.version,1);assert.equal(save.crafts.smith.rolls[0].d,10);assert.equal(save.crafts.scroll.when,'rush');
  const fresh=await open();await restore(fresh,save);
  assert.equal(await fresh.locator('#craft-scroll #when').inputValue(),'rush');
  assert.equal(await fresh.locator('#craft-scroll #o-cost').innerText(),'60 зм');
  await fresh.locator('[data-tab="smith"]').click();assert.equal(await fresh.locator('#craft-smith #o-p').innerText(),progress);
  await fresh.reload();await fresh.waitForFunction(()=>JDB&&ST.mat);
  assert.equal(await fresh.locator('#craft-smith #o-p').innerText(),progress);
  // Старые JSON не очищают уже перенесённую работу. Явное null в новом очищает.
  const legacy=structuredClone(save);delete legacy.crafts;
  await restore(fresh,legacy);assert.equal(await fresh.locator('#craft-smith #o-p').innerText(),progress);
  const empty=structuredClone(save);empty.crafts={version:1,smith:null,scroll:null};await restore(fresh,empty);
  assert.equal(await fresh.locator('#craft-smith #o-p').innerText(),'0/100');
  assert.equal(await fresh.locator('#craft-scroll #when').inputValue(),'2h');
  await restore(fresh,save);
  // Ошибка после записи ремёсел откатывает также настройки, планы и видимые формы.
  const before=await fresh.evaluate(()=>snapshot()),bad=structuredClone(empty);bad.settings.b='7';bad.state.mat.gold=77;
  await load(fresh,bad);await failWrites(fresh,'b',true);await fresh.locator('#restoreApply').click();
  await fresh.waitForFunction(()=>$('restoreSummary').textContent.includes('Предыдущее состояние возвращено'));
  await allowWrites(fresh);await fresh.locator('#restoreCancel').click();
  assert.equal(await fresh.evaluate(()=>ST.mat.gold),before.state.mat.gold);
  assert.equal(await fresh.locator('#b').inputValue(),before.settings.b||'5');
  assert.equal(await fresh.locator('#craft-smith #o-p').innerText(),progress);
  assert.equal(await fresh.locator('#craft-scroll #when').inputValue(),'rush');
  await fresh.reload();await fresh.waitForFunction(()=>JDB&&ST.mat);
  assert.equal(await fresh.locator('#craft-smith #o-p').innerText(),progress);
  // Враждебная строка импортируется как текст; обработчик не попадает в DOM.
  const hostile=await fresh.evaluate(()=>snapshot());
  const payload='<img src=x onerror="window.importExecuted=true">';
  hostile.state.fight={on:true,round:1,heals:[],coats:[],now:[payload]};hostile.settings.tab='belt';
  await restore(fresh,hostile);
  assert.equal(await fresh.locator('#fight .fnow').innerText(),payload);
  assert.equal(await fresh.locator('#fight .fnow img').count(),0);
  assert.equal(await fresh.evaluate(()=>window.importExecuted),undefined);
  for(const invalid of [{now:[{}]},{heals:[null]},{coats:[{who:'p1',n:'яд',ctl:false,left:'<img>'}]}]){
   const data=structuredClone(hostile);Object.assign(data.state.fight,invalid);
   await fresh.locator('#backupFile').setInputFiles({name:'bad-fight.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});
   await fresh.waitForFunction(()=>$('backupStatus').textContent.includes('Не восстановлено'));
   assert.equal(await fresh.locator('#restoreDialog').evaluate(d=>d.open),false);
  }
  // Ошибки записи встроенных ремёсел видны рядом с их формами.
  await failWrites(fresh,'smith-log-5');await fresh.locator('[data-tab="smith"]').click();
  await fresh.locator('#craft-smith #d20').fill('10');await fresh.locator('#craft-smith #add').click();
  assert.match(await fresh.locator('#craft-smith [role="status"]').innerText(),/Не удалось сохранить кузню/);
  assert.equal(await fresh.evaluate(()=>snapshot().crafts.smith.rolls.length),2,'backup includes the unsaved new roll');await allowWrites(fresh);
  await failWrites(fresh,'scroll-calc-3');await fresh.locator('[data-tab="scroll"]').click();
  await fresh.locator('#craft-scroll #when').selectOption('short');
  assert.match(await fresh.locator('#craft-scroll [role="status"]').innerText(),/Не удалось сохранить свитки/);
  assert.equal(await fresh.evaluate(()=>snapshot().crafts.scroll.when),'short');await allowWrites(fresh);
  assert.deepEqual(page.errors,[]);assert.deepEqual(fresh.errors,[]);
  console.log('PASS: storage failures, truthful status, no ghost undo, craft export to fresh browser, legacy/null, rollback and reload, imported HTML stays text');
 }finally{for(const c of contexts)await c.close();await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

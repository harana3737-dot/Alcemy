// Одна порция из «Прочего» переходит в эссенции без выдачи добычи заново.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
const name='Сгусток удержанной тени',legacyName='Эктоплазма полтергейста';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const context=await browser.newContext({acceptDownloads:true});const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',r=>r.abort());
  await page.goto(base+'/'+encodeURIComponent('Помощник варки.html'));await page.waitForFunction(()=>JDB&&ST.mat);
  const old=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-09-session17.json'),'utf8'));
  await page.evaluate(old=>mutate(()=>{ST=old.state;ST.mat.gold=123.45}),old);
  await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);
  const read=()=>page.evaluate(n=>({ess:ST.mat.ess.filter(e=>e.n===n),other:ST.mat.other.filter(e=>e.n===n||e.n==='Эктоплазма полтергейста'),gold:ST.mat.gold,bag:ST.bag,T:ST.T}),name);
  let actual=await read();assert.equal(actual.ess.length,1);assert.equal(actual.other.length,0);
  assert.equal(actual.ess[0].q,1);assert.equal(actual.ess[0].st,'fresh');
  assert.deepEqual(actual.ess[0].types,['Покров','Смерть/душа']);assert.equal(actual.ess[0].l,2);
  assert.equal(actual.ess[0].exp,undefined,'Закрытой колбе не назначается выдуманный срок');
  assert.equal(actual.gold,123.45);assert.deepEqual(actual.bag,old.state.bag);assert.equal(actual.T,old.state.T);
  await page.evaluate(()=>renderMat());
  assert.equal(await page.locator('#mat .bagi').filter({hasText:name}).count(),1);
  await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);assert.equal((await read()).ess[0].q,1);
  await page.evaluate(n=>mutate(()=>{ST.mat.ess=ST.mat.ess.filter(e=>e.n!==n)}),name);
  await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);assert.equal((await read()).ess.length,0,'Израсходованный трофей не восстанавливается');
  // Та же запись под новым именем и старый дубль не дают вторую порцию.
  const matrix=await page.evaluate(({old,n,legacy})=>{
   const mat=JSON.parse(JSON.stringify(old.state.mat));
   mat.other.push({n,q:1,note:'эссенция полтергейста; в закрытой колбе'});
   mat.ess.push({id:'already-processed',n,types:['Покров','Смерть/душа'],l:2,q:1,st:'good'});
   const changed=migrateHeldShadow(mat),again=migrateHeldShadow(mat);
   return {changed,again,ess:mat.ess.filter(e=>e.n===n),other:mat.other.filter(e=>e.n===n||e.n===legacy)};
  },{old,n:name,legacy:legacyName});
  assert.equal(matrix.changed,true);assert.equal(matrix.again,false);assert.equal(matrix.ess.length,1);
  assert.equal(matrix.ess[0].st,'good');assert.equal(matrix.ess[0].q,1);assert.equal(matrix.other.length,0);
  // Импорт старого JSON исправляется сразу, до перезагрузки страницы.
  const legacyFile=path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-09-session17.json');
  await page.locator('#backupFile').setInputFiles(legacyFile);await page.locator('#restoreDialog').waitFor({state:'visible'});
  const legacyBackup=page.waitForEvent('download');await page.locator('#restoreApply').click();await legacyBackup;
  await page.locator('#restoreDialog').waitFor({state:'hidden'});
  actual=await read();assert.equal(actual.ess.length,1);assert.equal(actual.ess[0].q,1);assert.equal(actual.other.length,0);
  // Сверяем весь перечень трофеев с актуальным учётом, а не только исправленный сгусток.
  const parity=await page.evaluate(()=>{
   const items=m=>['ess','other'].flatMap(k=>m[k].map(e=>({section:k,name:e.n,q:e.q}))).sort((a,b)=>a.name.localeCompare(b.name));
   return {actual:items(ST.mat),expected:items(SEED.mat)};
  });
  assert.deepEqual(parity.actual,parity.expected,'Старый снимок после поправок содержит весь подтверждённый перечень трофеев');
  // Старый снимок не содержит Искру: исправление обязано вернуть оба подтверждённых трофея.
  const spark='Искра заблудшей души';
  let sparks=await page.evaluate(n=>ST.mat.other.filter(e=>e.n===n),spark);
  assert.equal(sparks.length,1);assert.equal(sparks[0].q,1);
  assert.equal(await page.evaluate(()=>ST.mat.sparkConfirmed20261112),true);
  await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);
  assert.equal(await page.evaluate(n=>ST.mat.other.filter(e=>e.n===n).length,spark),1);
  await page.evaluate(n=>mutate(()=>{ST.mat.other=ST.mat.other.filter(e=>e.n!==n)}),spark);
  await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);
  assert.equal(await page.evaluate(n=>ST.mat.other.filter(e=>e.n===n).length,spark),0,'Удалённая после исправления Искра не появляется заново');
  const spentSnapshot=await page.evaluate(()=>snapshot());await page.evaluate(x=>validateSnapshot(x),spentSnapshot);
  assert.equal(spentSnapshot.state.mat.sparkConfirmed20261112,true,'Метка разового исправления входит в резервную копию');
  const file=path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-12-held-shadow.json');
  const snapshot=JSON.parse(fs.readFileSync(file,'utf8'));await page.evaluate(x=>validateSnapshot(x),snapshot);
  for(let i=0;i<2;i++){
   await page.locator('#backupFile').setInputFiles(file);await page.locator('#restoreDialog').waitFor({state:'visible'});
   const backup=page.waitForEvent('download');await page.locator('#restoreApply').click();await backup;
   await page.locator('#restoreDialog').waitFor({state:'hidden'});await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);
   actual=await read();assert.equal(actual.ess.length,1);assert.equal(actual.ess[0].q,1);assert.equal(actual.other.length,0);
   assert.equal(await page.evaluate(n=>ST.mat.other.filter(e=>e.n===n).length,spark),1,'Уже присутствующая Искра из снимка не удваивается');
  }
  assert.deepEqual(errors,[]);await context.close();console.log('PASS: both shadow names, x1 raw essence, preserved bag/gold/time/processed quality, no duplicate or replenishment, immediate legacy import, missing spark restored once and never replenished');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});

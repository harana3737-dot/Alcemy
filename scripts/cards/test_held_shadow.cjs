// Одна порция из «Прочего» переходит в эссенции без выдачи добычи заново.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
const name='Сгусток удержанной тени';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const context=await browser.newContext({acceptDownloads:true});const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',r=>r.abort());
  await page.goto(base+'/'+encodeURIComponent('Помощник варки.html'));await page.waitForFunction(()=>JDB&&ST.mat);
  const old=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-09-session17-essences.json'),'utf8'));
  await page.evaluate(old=>mutate(()=>{ST=old.state;ST.mat.gold=123.45}),old);
  await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);
  const read=()=>page.evaluate(n=>({ess:ST.mat.ess.filter(e=>e.n===n),other:ST.mat.other.filter(e=>e.n===n),gold:ST.mat.gold,bag:ST.bag,T:ST.T}),name);
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
  const file=path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-12-held-shadow.json');
  const snapshot=JSON.parse(fs.readFileSync(file,'utf8'));await page.evaluate(x=>validateSnapshot(x),snapshot);
  for(let i=0;i<2;i++){
   await page.locator('#backupFile').setInputFiles(file);await page.locator('#restoreDialog').waitFor({state:'visible'});
   const backup=page.waitForEvent('download');await page.locator('#restoreApply').click();await backup;
   await page.locator('#restoreDialog').waitFor({state:'hidden'});await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);
   actual=await read();assert.equal(actual.ess.length,1);assert.equal(actual.ess[0].q,1);assert.equal(actual.other.length,0);
  }
  assert.deepEqual(errors,[]);await context.close();console.log('PASS: held shadow x1, raw essence, preserved bag/gold/time, no duplicate or replenishment, snapshot restore');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});

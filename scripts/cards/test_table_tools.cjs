const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||['/usr/bin/chromium','/opt/pw-browsers/chromium'].find(f=>require('node:fs').existsSync(f)),headless:true,args:['--no-sandbox']});
 try {
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('https://**/*',r=>r.abort());
 await page.goto((process.env.ALCEMY_URL||'http://127.0.0.1:8770')+'/'+encodeURIComponent('Помощник варки.html'));
 await page.waitForFunction(()=>!!JDB&&!!ST.mat);
 assert.deepEqual(errors,[]);
 assert.match(await page.locator('#availability').innerText(),/Зелье лечения 1.1/);
 assert.equal(await page.locator('#avRecipe option').count(),1);
 assert.match(await page.locator('#out').innerText(),/Зелье лечения 1.1/);
 assert.doesNotMatch(await page.locator('#out').innerText(),/Выбери рецепт слева/);
 await page.locator('#avQty').fill('6');await page.locator('#avQty').dispatchEvent('change');
 assert.match(await page.locator('#avShopping').innerText(),/1.*0,1 зм/);
 const logic=await page.evaluate(()=>{
  const old=JSON.stringify(ST);ST.knownRecipes=[recipeKey(D.find(c=>c.n==='Подмога'))];
  const aid=D.find(c=>c.n==='Подмога');const first=supply(aid,1);ST.mat.herbs.push({k:'heal',l:2,q:2});
  const ready=supply(aid,1);ST.mat.ess.find(e=>e.id==='e4').exp=ST.T-1;const expired=supply(aid,1);
  const before=JSON.stringify(ST);supply(aid,2);supply(D.find(c=>c.k==='fl'),1);const pure=before===JSON.stringify(ST);
  ST.mat.ess.find(e=>e.id==='e4').exp=null;const shared=supply({...aid,e:'Тело II + Тело II'},1).deficits.find(d=>d.n.startsWith('Эссенция')).q;
  const state=snapshot();validateSnapshot(state);let rejects=0;
  for(const bad of [{...state,version:2},{...state,state:{...state.state,bag:[{n:'x',who:'bad',q:1}]}},JSON.parse('{"format":"alcemy-helper","__proto__":{}}')])try{validateSnapshot(bad)}catch(e){rejects++}
  ST=JSON.parse(old);return {first:first.deficits.length,ready:ready.ready,expired:expired.ready,pure,rejects,shared};
 });
 assert.deepEqual(logic,{first:1,ready:true,expired:false,pure:true,rejects:3,shared:1});
 await page.locator('#avMode').selectOption('all');await page.locator('#avRecipe').selectOption('Подмога');
 assert.equal(await page.locator('#out h2').innerText(),'Подмога');
 await page.locator('#avRecipe').selectOption('Яд 1.1');
 assert.equal(await page.locator('#out h2').innerText(),'Яд 1.1');
 await page.locator('#avRecipe').selectOption('Подмога');
 await page.locator('#avKnown').check();
 assert(await page.evaluate(()=>knows(D.find(c=>c.n==='Щит веры'))));
 await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);
 assert(await page.evaluate(()=>knows(D.find(c=>c.n==='Подмога'))));
 const save=await page.evaluate(async()=>{await JDB.collection('tracks').doc('test-root').set({name:'Корневая метка тест',group:'project',mode:'roll',target:30,current:0,done:false,log:[],cost:{type:'stage',mat:60,loss:[10,20,30]},rule:'СЛ 14'});return snapshot()});
 await page.locator('[data-tab="jour"]').click();
 const card=page.locator('.jc[data-id="test-root"]');await card.locator('input[aria-label="Сколько добавить"]').fill('11');
 await card.locator('select[aria-label="Исход подхода"]').selectOption('un');
 await card.getByRole('button',{name:'Добавить',exact:true}).click();
 await page.waitForFunction(()=>TR.find(t=>t.id==='test-root').current===5.5);
 const download=page.waitForEvent('download');await page.locator('#backupExport').click();const file=await download;const exported=JSON.parse(require('node:fs').readFileSync(await file.path(),'utf8'));assert.equal(exported.format,'alcemy-helper');assert.equal(exported.tracks.find(t=>t.id==='test-root').current,5.5);
 save.state.mat.gold=77.25;save.settings.m='2';
 await page.locator('#backupFile').setInputFiles({name:'restore.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(save))});
 await page.locator('#restoreApply').click();await page.waitForFunction(()=>ST.mat.gold===77.25&&TR.find(t=>t.id==='test-root').current===0);
 await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);assert.equal(await page.evaluate(()=>ST.mat.gold),77.25);
 const rollback=await page.evaluate(()=>{
  const s=snapshot();s.state.mat.gold=22;window.oldJDB=JDB;let fail=true;
  JDB={collection:()=>({doc:id=>{
   const d=oldJDB.collection('tracks').doc(id);
   return {...d,set:async value=>{if(fail){fail=false;throw Error('Проверочный сбой записи')}return d.set(value)}};
  }})};return s;
 });
 await page.locator('#backupFile').setInputFiles({name:'rollback.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(rollback))});await page.locator('#restoreApply').click();
 await page.waitForFunction(()=>document.getElementById('restoreSummary').textContent.includes('Предыдущее состояние возвращено'));assert.equal(await page.evaluate(()=>ST.mat.gold),77.25);await page.locator('#restoreCancel').click();await page.evaluate(()=>{JDB=oldJDB});
 const before=await page.evaluate(()=>JSON.stringify(ST));
 await page.locator('#backupFile').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{"version":99}')});
 await page.waitForFunction(()=>document.getElementById('backupStatus').textContent.includes('Не восстановлено'));assert.equal(await page.evaluate(()=>JSON.stringify(ST)),before);
 assert.deepEqual(errors,[]);console.log('PASS: availability, shortages, shared formulas, expired stock, purity, validation, 5.5 progress, export, restore, persistence');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

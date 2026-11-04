/* Regression checks for Shaerra's standalone notebook; no player storage is used. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const source=fs.readFileSync(path.join(__dirname,'..','Шаэрра','Руны Шаэрры.html'),'utf8');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || '/usr/bin/chromium',args:['--no-sandbox']});
 const errors=[];
 async function open(seed) {
  const c=await browser.newContext({viewport:{width:390,height:844}});
  await c.route('https://**/*',r=>r.abort());await c.route('http://shaerra.test/**',r=>r.fulfill({contentType:'text/html; charset=utf-8',body:source}));
  const p=await c.newPage();p.on('pageerror',e=>errors.push(e.message));await p.goto('http://shaerra.test/');
  if(seed){await p.evaluate(s=>{for(const [k,v] of Object.entries(s))localStorage.setItem(k,JSON.stringify(v));},seed);await p.reload();}
  return p;
 }
 const state=p=>p.evaluate(()=>JSON.parse(exportText()));
 async function transfer(p,bundle,mode='restore') {
  await p.locator('#backup').evaluate(e=>e.open=true);await p.locator('#impText').fill(JSON.stringify(bundle));
  await p.locator('#importMode').selectOption(mode);await p.locator('#imp').click();
 }
 try {
  const p=await open({'shaerra-log':[{a:15,b:1,d:'24.10.2026, 22:54',ev:'Ишида-сан и удача мёртвых',s1:'спасённые'}],
   'shaerra-day':{v:2,a:7,b:2,spent:{1:'союзник',2:''},tg:{1:'',2:'зомби'},evExp:'ожидание',ev:'черновик вечера',evFal:'сомнение'}});
  assert.equal(await p.locator('#d1').inputValue(),'7');assert.equal(await p.locator('#tg2').inputValue(),'зомби');
  assert.equal(await p.locator('#ev').inputValue(),'черновик вечера');
  await p.locator('#prophecy').fill('Сегодня кто-то пойдёт по дороге. А в конце сомкнутся цепи.');
  await p.locator('#gameDate').fill('День пути 3');
  await p.reload();assert.match(await p.locator('#prophecy').inputValue(),/сомкнутся цепи/);
  const current=await state(p),oldPrediction=current.log[0].prophecy;
  assert.equal(current.v,3);assert.equal(current.day.tg[2],'зомби');assert.equal(current.day.gameDate,'День пути 3');
  await p.evaluate(()=>{FLOW_T[15]='Текст обновлён';renderLog();});assert.match(await p.locator('#log').innerText(),new RegExp(oldPrediction.split('.')[0]));
  await p.locator('[data-edit]').click();await p.locator('#editEv').fill('Позднее: Ишида-сан <img src=x onerror=alert(1)>');
  await p.locator('#editGameDate').fill('День спасения');await p.locator('#editProphecy').fill('Так прозвучало в игре');
  await p.locator('#logEditor button[type=submit]').click();assert.deepEqual((await state(p)).day,current.day);
  assert.equal(await p.locator('#log img').count(),0);
  await p.locator('#logSearch').fill('ишида');assert.equal(await p.locator('[data-edit]').count(),1);
  await p.locator('#logRune').selectOption('2');assert.equal(await p.locator('[data-edit]').count(),0);
  await p.locator('#logRune').selectOption('15');assert.equal(await p.locator('[data-edit]').count(),1);
  await p.locator('#logSearch').fill('');await p.locator('#logRune').selectOption('');
  const backup=await state(p),q=await open();await q.locator('#prophecy').fill('Свой день до переноса');const before=await state(q);
  await transfer(q,backup);assert.deepEqual(await state(q),backup);await q.reload();assert.deepEqual(await state(q),backup);
  await q.locator('#backup').evaluate(e=>e.open=true);await q.locator('#undoImport').click();assert.deepEqual(await state(q),before);
  await transfer(q,backup,'merge');assert.deepEqual((await state(q)).day,before.day);assert.equal((await state(q)).log.length,1);
  await transfer(q,backup,'merge');assert.equal((await state(q)).log.length,1);
  await transfer(q,{v:3,log:backup.log,day:{a:21,b:2}});assert.match(await q.locator('#impMsg').innerText(),/Повреждён/);
  assert.deepEqual((await state(q)).day,before.day);
  await transfer(q,backup.log);assert.match(await q.locator('#impMsg').innerText(),/только история/);
  const untouched=await state(q);
  await transfer(q,{v:3,log:backup.log,day:{a:7,b:2,spent:{1:{bad:'data'}}}});assert.deepEqual(await state(q),untouched);
  await transfer(q,{v:3,log:[{a:7,b:2,prophecy:{bad:'data'}}],day:backup.day});assert.deepEqual(await state(q),untouched);
  // Simulated failure on the second storage write must roll back persisted and in-memory state.
  const saved=await state(q);
  await q.evaluate(()=>{const original=Storage.prototype.setItem;window.restoreStorage=()=>Storage.prototype.setItem=original;
    let fail=true;Storage.prototype.setItem=function(k,v){if(k==='shaerra-day' && fail){fail=false;throw Error('quota');}return original.call(this,k,v);};});
  await transfer(q,backup);assert.deepEqual(await state(q),saved);assert.match(await q.locator('#impMsg').innerText(),/отменён/);
  await q.evaluate(()=>window.restoreStorage());await q.reload();assert.deepEqual(await state(q),saved);
  // Closing a day snapshots the author's words and cannot be repeated after reload.
  await p.locator('#save').click();assert.equal((await state(p)).log.length,2);
  assert.equal((await state(p)).log[0].prophecy,backup.day.prophecy);
  await p.reload();await p.locator('#save').click();assert.equal((await state(p)).log.length,2);
  await p.locator('[data-edit]').first().click();const originalLog=await p.evaluate(()=>JSON.stringify(LOG));
  await p.locator('#editEv').fill('Не потерять несохранённую правку');
  await p.evaluate(()=>{const original=Storage.prototype.setItem;window.restoreStorage=()=>Storage.prototype.setItem=original;Storage.prototype.setItem=function(){throw Error('quota');};});
  await p.locator('#logEditor button[type=submit]').click();assert.equal(await p.evaluate(()=>JSON.stringify(LOG)),originalLog);
  assert.match(await p.locator('#editEv').inputValue(),/Не потерять/);await p.evaluate(()=>window.restoreStorage());await p.locator('#cancelEdit').click();
  // Empty history import, duplicate records in one file, version guard, preview export.
  await transfer(q,{v:3,log:[...backup.log,...backup.log],day:backup.day},'merge');assert.equal((await state(q)).log.length,1);
  await transfer(q,{v:999,log:[],day:null});assert.match(await q.locator('#impMsg').innerText(),/не поддерживается/);
  const own=await state(q);await q.goto('http://shaerra.test/#20-20');assert.deepEqual(await state(q),own);
  await q.locator('#save').click();assert.deepEqual(await state(q),own);await q.locator('#backDay').click();
  // View mode keeps mechanics and storage intact; all rune combinations still render.
  const stable=await state(q);await q.locator('#compact').click();assert.equal(await q.locator('#compact').getAttribute('aria-pressed'),'true');
  assert.deepEqual(await state(q),stable);
  for(const width of [360,390,1280]){await q.setViewportSize({width,height:844});assert.ok(await q.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`width ${width}`);}
  await q.reload();assert.equal(await q.locator('#compact').getAttribute('aria-pressed'),'true');
  assert.ok(await q.evaluate(()=>{CUSTOM=false;for(let a=1;a<=20;a++)for(let b=1;b<=20;b++){A=a;B=b;render(false);if(!document.getElementById('omen').textContent.trim())return false;}return true;}));
  // File-based round trip uses the same payload and works without clipboard access.
  const f=await open();await f.locator('#save').click();assert.equal((await state(f)).log.length,0);await f.locator('#backup').evaluate(e=>e.open=true);
  await f.locator('#importFile').setInputFiles({name:'shaerra-save.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(backup))});
  await f.waitForFunction(()=>document.getElementById('impText').value.includes('День пути 3'));
  await f.locator('#importMode').selectOption('restore');await f.locator('#imp').click();assert.deepEqual(await state(f),backup);
  const downloadEvent=f.waitForEvent('download');await f.locator('#download').click();const download=await downloadEvent;
  assert.equal(download.suggestedFilename(),'shaerra-save.json');
  const downloaded=JSON.parse(fs.readFileSync(await download.path(),'utf8'));assert.deepEqual(downloaded,backup);
  await f.setViewportSize({width:360,height:844});await f.locator('#compact').click();
  await f.screenshot({path:process.env.SHAERRA_SCREENSHOT || '/tmp/shaerra-compact.png',fullPage:true});
  // Anchor navigation must keep a draft even when browser storage refuses writes.
  const nav=await open();await nav.locator('#prophecy').fill('Мой день');
  await nav.evaluate(()=>{const original=Storage.prototype.setItem;window.restoreStorage=()=>Storage.prototype.setItem=original;Storage.prototype.setItem=function(){throw Error('quota');};});
  await nav.locator('#ev').fill('Черновик при отказе хранилища');await nav.locator('a[href="#journal"]').click();
  assert.equal(await nav.locator('#ev').inputValue(),'Черновик при отказе хранилища');
  await nav.evaluate(()=>window.restoreStorage());await nav.locator('#ev').dispatchEvent('input');await nav.reload();
  assert.equal(await nav.locator('#ev').inputValue(),'Черновик при отказе хранилища');
  // The delivered artifact is normally opened as a local HTML file.
  const localContext=await browser.newContext();await localContext.route('https://**/*',r=>r.abort());
  const local=await localContext.newPage();local.on('pageerror',e=>errors.push(e.message));
  let localAllowed=true;
  try {await local.goto(require('node:url').pathToFileURL(path.join(__dirname,'..','Шаэрра','Руны Шаэрры.html')).href);}
  catch(e) {if(String(e.message).includes('ERR_BLOCKED_BY_ADMINISTRATOR')) {localAllowed=false;console.log('SKIP: file:// navigation is prohibited by the managed browser policy; standalone content tested over isolated HTTP with external requests blocked.');}else throw e;}
  if(localAllowed) {
    await local.locator('#d1').fill('7');await local.locator('#d1').dispatchEvent('change');
    await local.locator('#d2').fill('2');await local.locator('#d2').dispatchEvent('change');
    await local.locator('#prophecy').fill('Моё предсказание в локальном файле');await local.locator('#save').click();
    assert.equal((await state(local)).log.length,1);await local.reload();assert.equal((await state(local)).log[0].prophecy,'Моё предсказание в локальном файле');
    await local.locator('#save').click();assert.equal((await state(local)).log.length,1);
  }
  assert.deepEqual(errors,[]);
  console.log('PASS: Shaerra legacy migration, custom prophecy, history edit/search, full restore/reload/undo, merge dedup, malformed input, storage rollback, immutable old text, preview, compact/mobile, 400 pairs');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});

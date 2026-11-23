// Конечный LSS сессии17: импорт не выдаёт подарки дважды и не повторяет расходы.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/opt/pw-browsers/chromium',headless:true,args:['--no-sandbox']});
 try{
  const context=await browser.newContext({acceptDownloads:true}),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',r=>r.fulfill({status:200,body:''}));
  await page.goto(base+'/'+encodeURIComponent('Помощник варки.html'));await page.waitForFunction(()=>JDB&&ST.mat);
  const file=path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-09-session17.json');
  async function restore(snapshot=file){
   await page.locator('#backupFile').setInputFiles(snapshot);await page.locator('#restoreDialog').waitFor({state:'visible'});
   const download=page.waitForEvent('download');await page.locator('#restoreApply').click();await download;
   await page.locator('#restoreDialog').waitFor({state:'hidden'});
  }
  async function check(){
   const a=await page.evaluate(()=>({hp:talis().hp,sp:talis().sp+talis().meta,slots:talis().slots,gold:ST.mat.gold,
    q:['Зелье 3.3','Зелье лечения 2.2','Зелье лечения 1.1'].map(n=>ST.bag.filter(b=>b.who==='p1'&&b.n===n).reduce((a,b)=>a+b.q,0)),
    growth:TR.find(t=>t.id==='mastery-2-3').current,known22:ST.knownRecipes.some(n=>/2\.2/.test(n))}));
   assert.deepEqual(a,{hp:41,sp:3,slots:{1:1,2:1,3:0},gold:108.18,q:[2,2,2],growth:4,known22:false});
  }
  await restore();await check();await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);await check();
  // В действующей сумке расходы уже внесены, но метка старой версии листа осталась.
  const old=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-02-recovered.json'),'utf8'));
  await page.evaluate(old=>mutate(()=>{ST.seed=old.seed;ST.seedQ=old.seedQ}),old.state);
  await page.reload();await page.waitForFunction(()=>JDB&&ST.mat);await check();
  await restore();await check();
  const current=path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-22-talis-inventory.json');
  for(let i=0;i<2;i++){
   await restore(current);await page.reload();await page.waitForFunction(()=>JDB&&ST.mat&&TR.length);
   const now=await page.evaluate(()=>{
    const c=ST.mat.cat.find(x=>x.id==='brass-catalyst-20261122');
    return {gold:ST.mat.gold,hp:talis().hp,sp:sorceryTotal(),cap:cmax(c),safe:stab(c),
     growth:TR.find(t=>t.id==='mastery-2-3').current,tough:TR.find(t=>t.id==='project-tough').current,
     hours:ST.hrs.undated[0].h,total:ST.hrs.total,T:ST.T,
     shadow:ST.mat.ess.some(e=>e.n==='Сгусток удержанной тени')};
   });
   assert.deepEqual(now,{gold:77.79,hp:42,sp:6,cap:3,safe:3,growth:5,tough:44,
    hours:10,total:20,T:old.state.T,shadow:false});
   await page.locator('[data-tab="jour"]').click();
   assert.match(await page.locator('#jhrs').innerText(),/Часы без игрового дня.*10 ч/s);
  }
  const session18=path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-23-session18.json');
  await restore(session18);
  await page.reload();
  await page.waitForFunction(()=>JDB&&ST.mat&&TR.length);
  assert.deepEqual(await page.evaluate(()=>({
    day:dayOf(ST.T),minute:ST.T%1440,hours:ST.hrs.total,gold:ST.mat.gold,
    talisWarCaster:TR.find(t=>t.id==='project-war-caster').current,
  })),{day:17,minute:480,hours:20,gold:77.79,talisWarCaster:6});
  assert.deepEqual(errors,[]);await context.close();
  console.log('PASS: session17 LSS resources, pooled points, gift once, no duplicate consumption, reload and repeated import');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});

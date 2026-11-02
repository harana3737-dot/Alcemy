// Восстановление реального среза: часы, рост, сырьё чернил и отсутствие повторных списаний.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://**/*',r=>r.abort());
  await page.goto((process.env.ALCEMY_URL||'http://127.0.0.1:8770')+'/'+encodeURIComponent('Помощник варки.html'));
  await page.waitForFunction(()=>JDB&&ST.mat);
  const file=path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-02-session16.json');
  async function restore(){
   await page.locator('#backupFile').setInputFiles(file);
   await page.locator('#restoreDialog').waitFor({state:'visible'});
   const backup=page.waitForEvent('download');
   await page.locator('#restoreApply').click();await backup;
   await page.locator('#restoreDialog').waitFor({state:'hidden'});
  }
  async function check(){
   const actual=await page.evaluate(()=>({day:dayOf(ST.T),time:ST.T%1440,gold:ST.mat.gold,
    hp:talis().hp,sp:talis().sp,meta:talis().meta,slots:talis().slots,
    mastery:TR.find(t=>t.id==='mastery-2-3').current,
    ink:TR.find(t=>t.id==='research-ink').done,
    root1:TR.find(t=>t.id==='project-serebryanka-1').paid,
    root2:TR.find(t=>t.id==='project-root-2').current,
    tough:TR.find(t=>t.id==='project-tough').current,
    war:TR.find(t=>t.id==='project-war-caster').current,
    hours:ST.hrs.total,today:ST.ledger['16'].h,
    heal:herbValue('heal',1),poison:herbValue('poison',1),
    higherHeal:herbValue('heal',2),higherPoison:herbValue('poison',2),
    powder:ST.mat.ess.some(e=>e.n==='Костяная пыль'),
    mixedOther:ST.mat.other.some(o=>o.n==='Смешанные лечебные и ядовитые травы'),
    seed:ST.matSeed===SEED.mid,healing:ST.bag.find(b=>b.who==='p1'&&b.n==='Зелье 3.3').q}));
   assert.deepEqual(actual,{day:16,time:840,gold:108.18,hp:37,sp:4,meta:2,slots:{1:2,2:3,3:1},
    mastery:4,ink:true,root1:true,root2:38,tough:34,war:6,hours:10,today:0,
    heal:15.5,poison:15.4,higherHeal:0,higherPoison:0,powder:false,mixedOther:false,seed:true,healing:3});
   await page.locator('[data-tab="jour"]').click();
   assert.match(await page.locator('#jhrs').innerText(),/День 16.*14:00/);
   assert.equal(await page.locator('.jc[data-id="project-serebryanka-1"]').getByRole('button',{name:/Завершить этап/}).count(),0);
   const ink=page.locator('#jink');
   await ink.locator('.il').selectOption('1');
   assert.doesNotMatch(await ink.locator('.ires').innerText(),/не хватает/);
   assert.match(await ink.locator('.ires').innerText(),/15,5/);
   await page.locator('[data-tab="brewing-plan"]').click();
   assert.match(await page.locator('#bpForecast').innerText(),/11 из 15/);
  }
  await restore();await check();
  await page.reload();await page.waitForFunction(()=>JDB&&ST.mat&&TR.length);await check();
  await restore();await check();
  assert.deepEqual(errors,[]);
  console.log('PASS: session 16 restore, day 16 14:00, 4/15 growth, ink stock I only, resources, paid stage, reload and repeated import');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

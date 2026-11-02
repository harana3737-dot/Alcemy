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
  let file=path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-02-session16.json');
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
   await page.locator('[data-tab="brew"]').click();
   await page.locator('#avMode').selectOption('known');
   assert.equal(await page.locator('#avRecipe option[value="Чернила"]').count(),1);
   const before=await page.evaluate(()=>JSON.stringify(ST));
   await page.locator('#avRecipe').selectOption('Чернила');
   assert(await page.locator('#avKnown').isChecked());
   assert(await page.locator('#avKnown').isDisabled());
   assert.match(await page.locator('#out').innerText(),/Рецепт освоен/);
   assert.doesNotMatch(await page.locator('#avShopping').innerText(),/Материалов хватает/);
   assert.equal(await page.evaluate(()=>JSON.stringify(ST)),before);
   assert(!(await page.evaluate(()=>recommendBrews({budget:1000,hours:100,need:'',search:'',stockOnly:false}).some(r=>r.c.k==='ink'))));
   await page.locator('#avOpen').click();
   assert.equal(await page.locator('[data-tab="jour"]').getAttribute('aria-selected'),'true');
   const ink=page.locator('#jink');
   await ink.locator('.il').selectOption('1');
   assert.doesNotMatch(await ink.locator('.ires').innerText(),/не хватает/);
   assert.match(await ink.locator('.ires').innerText(),/15,5/);
   await page.locator('[data-tab="brewing-plan"]').click();
   assert.match(await page.locator('#bpForecast').innerText(),/11 из 15/);
   await page.locator('#projectsOpen').click();
   const project=page.locator('#journal-project .jc[data-id="project-root-2"]');
   assert.match(await project.innerText(),/38 \/ 45/);
   const bounds=await page.locator('#journal-project').boundingBox();
   assert(bounds.y>=-1&&bounds.y<844,'projects shortcut must bring the section onto the phone screen: '+JSON.stringify(bounds));
  }
  await restore();await check();
  file=path.resolve(__dirname,'../../Источники/Сохранения/alcemy-save-2026-11-02-recovered.json');
  await restore();await check();
  assert.equal(await page.evaluate(()=>knows(BASIC[0])),true,'recovery snapshot restores known healing 1.1');
  await page.reload();await page.waitForFunction(()=>JDB&&ST.mat&&TR.length);await check();
  await restore();await check();
  assert.deepEqual(errors,[]);
  console.log('PASS: session 16 restore, day 16 14:00, 4/15 growth, known ink and recipe routing, project shortcut, resources, paid stage, reload and repeated import');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

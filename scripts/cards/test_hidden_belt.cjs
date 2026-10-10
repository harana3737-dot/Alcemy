const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://**/*',r=>r.abort());
  await page.goto((process.env.ALCEMY_URL||'http://127.0.0.1:8770')+'/'+encodeURIComponent('Помощник варки.html'));
  await page.waitForFunction(()=>JDB&&ST.mat);
  await page.locator('[data-tab="belt"]').click();
  const checked=await page.evaluate(()=>{
   const bagForm=$('bagAdd'),matFirst=$('mat').firstElementChild;
   const old=JSON.stringify(ST);tab('jour');
   mutate(()=>{ST.mat.gold=77.25;ST.people[0].name='Проверка скрытого пояса';ST.bag.push({n:'Проверочный предмет',q:3,who:ST.people[0].id});logx('Скрытый пояс')});
   const retained=bagForm===$('bagAdd')&&matFirst===$('mat').firstElementChild;
   const saved=JSON.parse(ls.get('belt')).mat.gold===77.25;
   tab('belt');
   const visible=$('bag').textContent.includes('Проверочный предмет')&&$('mat').querySelector('input[aria-label="Монеты, зм"]').value==='77.25'&&$('log').textContent.includes('Скрытый пояс');
   $('undo').click();const restored=ST.mat.gold===JSON.parse(old).mat.gold&&!ST.bag.some(x=>x.n==='Проверочный предмет');
   return {retained,saved,visible,restored};
  });
  assert.deepEqual(checked,{retained:true,saved:true,visible:true,restored:true});
  assert.deepEqual(errors,[]);console.log('PASS: hidden belt DOM retained, state persisted, tab refreshed, undo restored');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

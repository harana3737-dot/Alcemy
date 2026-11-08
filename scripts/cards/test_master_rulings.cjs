// Ж-148: натуральная20 сохраняет потраченный катализатор; инструмент не списывается.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.ALCEMY_URL||'http://127.0.0.1:8770';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/opt/pw-browsers/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://**/*',r=>r.fulfill({status:200,body:''}));
  await page.goto(base+'/'+encodeURIComponent('Помощник варки.html'));await page.waitForFunction(()=>JDB&&ST.mat);
  const material=await page.evaluate(()=>{
   const c=D.find(c=>c.n==='Силовая клетка');
   ST.mat.other.push({n:'рубиновая пыль',q:1});
   const gold=ST.mat.gold,box=document.createElement('div');document.body.append(box);
   box._plan={att:1,cm:{...c.cm,q:1}};box.innerHTML='<select class="res-m"><option value="other">пыль</option></select>';
   applyUse(box);box.remove();return {use:c.cm.use,goldBefore:gold,goldAfter:ST.mat.gold,q:ST.mat.other.at(-1).q};
  });
  assert.equal(material.use,false);assert.equal(material.goldBefore,material.goldAfter);assert.equal(material.q,1);
  await page.evaluate(()=>{
   document.getElementById('m').value='5';const box=document.createElement('div');box.id='ruling-brew';document.body.append(box);
   recForm(box,{name:'Зелье 5.5',lvl:5,noUse:true});
  });
  await page.locator('#ruling-brew [data-k="n20"]').fill('1');
  await page.locator('#ruling-brew .b20s').selectOption('Выше уровнем');
  await page.locator('#ruling-brew .rgo').click();
  await page.waitForFunction(()=>ST.bag.some(b=>b.n==='Зелье 6.6'&&b.note?.includes('варка 5.5')));
  const bag=await page.evaluate(()=>ST.bag.find(b=>b.n==='Зелье 6.6'&&b.note?.includes('варка 5.5')));
  assert.match(bag.note,/катализатор I \(варка 5\.5\)/);
  const growth=await page.evaluate(()=>TR.find(t=>t.id==='mastery-5-6')?.current);assert.equal(growth,2);
  assert.deepEqual(errors,[]);console.log('Ж-148: катализатор I при 5.5 → 6.6, рост исходного уровня, многоразовая пыль — OK');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});

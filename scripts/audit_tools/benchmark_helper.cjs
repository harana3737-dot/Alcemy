// Замеры на временной сборке; не тест с порогом времени.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require('playwright');
const args=process.argv.slice(2);function option(k,d){const i=args.indexOf(k);return i<0?d:args[i+1]}
const root=path.resolve(option('--root','.')),output=option('--output',null),samples=Number(option('--samples','15'));
if(!Number.isInteger(samples)||samples<5)throw Error('--samples >= 5');
const html=fs.readFileSync(path.join(root,'Помощник варки.html'));
const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html; charset=utf-8');res.end(html)});
const percentile=(xs,q)=>xs.slice().sort((a,b)=>a-b)[Math.ceil(xs.length*q)-1];
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const result={html_sha256:require('node:crypto').createHash('sha256').update(html).digest('hex'),method:'Chromium headless, CPU x4; synchronous handler + forced layout; 3 warmups; raw milliseconds',bytes:html.length,samples,cases:[]};
 try{
 for(const width of [1280,360])for(const size of ['normal','large']){
  const page=await browser.newPage({viewport:{width,height:800}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',r=>r.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}/`);await page.waitForFunction(()=>JDB&&ST.mat);
  const session=await page.context().newCDPSession(page);await session.send('Emulation.setCPUThrottlingRate',{rate:4});
  await page.evaluate(size=>{
   if(size==='large'){
    ST.bag=Array.from({length:200},(_,i)=>({n:D[i%D.length].n,q:1,who:ST.people[0].id}));
    ST.log=Array.from({length:80},(_,i)=>({T:ST.T,t:`Запись ${i}`}));
    TR=Array.from({length:80},(_,i)=>({id:`bench-${i}`,name:`Исследование ${i}`,group:'project',mode:'roll',target:30,current:0,done:false,log:[]}));
   }
   window.benchState=JSON.stringify(ST);window.benchTracks=JSON.stringify(TR);
   window.benchCounts={};for(const name of ['renderBag','renderPeople','renderMat','renderBelt','renderJournal','renderAvailability']){
    const original=window[name];window[name]=function(...a){benchCounts[name]=(benchCounts[name]||0)+1;return original(...a)};
   }
  },size);
  for(const action of ['bag_add','journal_mutation','journal_open']){
   const times=[],counts=[];
   for(let i=-3;i<samples;i++){
    await page.evaluate(action=>{ST=JSON.parse(benchState);TR=JSON.parse(benchTracks);UNDO=[];tab(action==='journal_mutation'?'jour':'belt')},action);
    await page.waitForTimeout(30);
    const row=await page.evaluate(action=>{
     benchCounts={};const t=performance.now();
     if(action==='bag_add'){$('bagN').value='Зелье лечения 1.1';$('bagQ').value='1';$('bagAdd').click()}
     else if(action==='journal_mutation')mutate(()=>{ST.T+=1});
     else tab('jour');
     void document.body.offsetHeight;return {ms:performance.now()-t,counts:benchCounts};
    },action);
    if(i>=0){times.push(row.ms);counts.push(row.counts)}
   }
   result.cases.push({width,size,action,median_ms:percentile(times,.5),p95_ms:percentile(times,.95),times,counts});
  }
  if(errors.length)throw Error(errors.join('\n'));await page.close();
 }
 result.browser=browser.version();if(output)fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify({...result,cases:result.cases.map(({times,counts,...r})=>r)},null,2));
 }finally{await browser.close();await new Promise(r=>server.close(r))}
})().catch(e=>{console.error(e);server.close();process.exitCode=1});

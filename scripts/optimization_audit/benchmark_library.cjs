// Измеряет фильтр и подсветку старой или новой библиотеки; checkout не меняет.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require('playwright');
const args=process.argv.slice(2);
function option(key,fallback){const i=args.indexOf(key);return i<0?fallback:args[i+1];}
const root=path.resolve(option('--root','.')),output=option('--output',null);
const samples=Number(option('--samples','7'));
if(!Number.isInteger(samples)||samples<3)throw Error('--samples >= 3');
const html=fs.readFileSync(path.join(root,'Для игрока — логи, записки и предыстория.html'));
const server=http.createServer((request,response)=>{response.setHeader('Content-Type','text/html; charset=utf-8');response.end(html);});
const median=values=>values.slice().sort((a,b)=>a-b)[Math.floor(values.length/2)];
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try{
    browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
    const page=await browser.newPage(),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    const session=await page.context().newCDPSession(page);
    await session.send('Emulation.setCPUThrottlingRate',{rate:4});
    const cases=[];
    for(const query of ['на','Талис','гильдия']){
      const rows=[];
      for(let i=-2;i<samples;i++){
        await page.evaluate(()=>{search.value='';filter();});
        await page.waitForFunction(()=>document.getElementById('materials').getAttribute('aria-busy')!=='true');
        const row=await page.evaluate(async query=>{
          search.value=query;const start=performance.now();filter();clearTimeout(pending);
          void document.body.offsetHeight;const filterMs=performance.now()-start;
          const box=document.getElementById('materials'),began=performance.now();
          await new Promise((resolve,reject)=>{
            if(box.getAttribute('aria-busy')!=='true'){highlight(fold(query));resolve();return;}
            const timeout=setTimeout(()=>{observer.disconnect();reject(Error('Подсветка не завершилась за 30 с'));},30000);
            const observer=new MutationObserver(()=>{if(box.getAttribute('aria-busy')==='false'){clearTimeout(timeout);observer.disconnect();resolve();}});
            observer.observe(box,{attributes:true,attributeFilter:['aria-busy']});
            highlight(fold(query),searchVersion);
          });
          void document.body.offsetHeight;const highlightMs=performance.now()-began;
          const matches=document.querySelectorAll('.text mark').length;
          const next=performance.now();search.value=query+'а';filter();void document.body.offsetHeight;
          return {filter_ms:filterMs,highlight_ms:highlightMs,next_input_ms:performance.now()-next,matches};
        },query);
        if(i>=0)rows.push(row);
      }
      cases.push({query,medians:Object.fromEntries(['filter_ms','highlight_ms','next_input_ms'].map(key=>[key,median(rows.map(row=>row[key]))])),samples:rows});
    }
    if(errors.length)throw Error(errors.join('\n'));
    const result={browser:browser.version(),html_sha256:require('node:crypto').createHash('sha256').update(html).digest('hex'),method:'Chromium CPU x4; 2 warmups; forced layout; highlighting excludes 150 ms debounce, includes yielded tasks',cases};
    if(output)fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify({...result,cases:cases.map(({samples,...row})=>row)},null,2));
  }finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});

const {chromium}=require('playwright');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'alcemy-phone-')),file=path.join(dir,'phone.html'),root=path.resolve(__dirname,'../..');
 execFileSync('python3',['-B',path.join(root,'scripts/audit_tools/build_mobile_check.py'),'--root',root,'--output',file]);
 const server=http.createServer((_,res)=>{res.setHeader('Content-Type','text/html; charset=utf-8');res.end(fs.readFileSync(file))});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:360,height:800}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',r=>r.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  const child=page.frames().find(f=>f.parentFrame());await child.waitForFunction(()=>JDB&&ST.mat);
  const data=await child.evaluate(()=>{const data=snapshot();data.state.people[0].name='PRIVATE_TEST_PERSON';data.state.log.push({T:ST.T,t:'PRIVATE_TEST_LOG'});return data});
  await page.evaluate(()=>localStorage.setItem('belt','PRIVATE_ORIGINAL_STATE'));
  await page.locator('#save').setInputFiles({name:'working.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});
  await page.locator('#start').click();await page.waitForFunction(()=>report||document.getElementById('status').textContent.includes('не выполнена'),null,{timeout:90000});
  const result=await page.evaluate(()=>report);assert(result,await page.locator('#status').innerText());assert.equal(result.results.length,5);
  assert.equal(result.ok,true);assert(result.results.every(r=>r.samples.length===15));
  assert(!JSON.stringify(result).includes('PRIVATE_TEST'));assert.equal(await page.evaluate(()=>localStorage.getItem('belt')),'PRIVATE_ORIGINAL_STATE');
  const download=page.waitForEvent('download');await page.locator('#download').click();const item=await download;assert.equal(JSON.parse(fs.readFileSync(await item.path())).format,'alcemy-phone-check');
  assert.deepEqual(errors,[]);console.log('PASS: isolated working snapshot, five phone actions, undo, private data absent from report, original storage preserved');
 }finally{await browser.close();await new Promise(r=>server.close(r));fs.rmSync(dir,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1});

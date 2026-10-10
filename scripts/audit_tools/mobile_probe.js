// Выполняется только в изолированной испытательной копии помощника.
addEventListener('message',async event=>{
 if(event.source!==parent||event.data?.type!=='alcemy-phone-start')return;
 const send=value=>parent.postMessage({type:'alcemy-phone-result',...value},'*');
 try{
  let wait=0;while(!JDB||!ST.mat){if(++wait>500)throw Error('init');await new Promise(r=>setTimeout(r,10))}
  if(event.data.snapshot){const data=validateSnapshot(event.data.snapshot);ST=structuredClone(data.state);TR=structuredClone(data.tracks);for(const [k,v] of Object.entries(data.settings))ls.set(k,v)}
  renderBelt();tab('belt');
  const base=JSON.stringify(ST),tracks=JSON.stringify(TR);
  const results=[];const pct=(xs,q)=>xs.slice().sort((a,b)=>a-b)[Math.ceil(xs.length*q)-1];
  for(const action of ['bag_add','undo','journal_open','journal_update','combat_turn']){
   const samples=[];
   for(let i=-3;i<15;i++){
    ST=JSON.parse(base);TR=JSON.parse(tracks);UNDO=[];
    if(action==='combat_turn'){Object.assign(fight(),{on:true,round:1,sub:0,turned:false});tab('belt')}
    else tab(action==='journal_update'?'jour':'belt');
    if(action==='undo')mutate(()=>{ST.T+=1});
    await new Promise(r=>setTimeout(r,20));
    const t=performance.now();
    if(action==='bag_add'){$('bagN').value='Зелье лечения 1.1';$('bagQ').value='1';$('bagAdd').click()}
    if(action==='undo')$('undo').click();
    if(action==='journal_open')tab('jour');
    if(action==='journal_update')mutate(()=>{ST.T+=1});
    if(action==='combat_turn')$('fTurn').click();
    void document.body.offsetHeight;const handler=performance.now()-t;
    await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('background')),2000);requestAnimationFrame(()=>requestAnimationFrame(()=>{clearTimeout(timer);resolve()}))});
    if(i>=0)samples.push({handler_ms:handler,two_frames_ms:performance.now()-t});
   }
   results.push({action,median_handler_ms:pct(samples.map(x=>x.handler_ms),.5),p95_handler_ms:pct(samples.map(x=>x.handler_ms),.95),samples});
   parent.postMessage({type:'alcemy-phone-progress',completed:results.length},'*');
  }
  // Отдельная проверка отмены; отметка времени сохранения в сравнение не входит.
  ST=JSON.parse(base);TR=JSON.parse(tracks);UNDO=[];tab('belt');
  const normalized=s=>{const copy=structuredClone(s);delete copy.u;return JSON.stringify(copy)};
  const before=normalized(ST);mutate(()=>{ST.T+=1});$('undo').click();
  if(normalized(ST)!==before)throw Error('undo');
  const counts={people:ST.people.length,bag:ST.bag.length,tracks:TR.length,log:ST.log.length};
  send({ok:true,counts,results,width:innerWidth});
 }catch(_){send({ok:false,error:'Проверка не выполнена: сохранение несовместимо или действие завершилось ошибкой.'})}
});

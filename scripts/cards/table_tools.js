// Доступная варка и перенос полного сохранения. Встраивается в HTML генератором.
const BASIC = ['heal','poison'].flatMap(kind=>Array.from({length:10},(_,i)=>({
  n:(kind==='heal'?'Зелье лечения ':'Яд ')+(i+1)+'.'+(i+1),l:i+1,k:'basic',b:kind==='heal'?'лечебная':'ядовитая',e:'',f:''
})));
const RECIPES = [...BASIC,...D];
const tier=l=>l<=2?2:l<=5?5:l<=7?7:9;
function recipeKey(c){
  if(c.k==='basic'||!c.f||c.l===10)return c.n;
  if(['chg','rea','fl','psn','oilw','salve','oils'].includes(c.k))return c.f;
  return c.f+' · '+({2:'обычная',5:'необычная',7:'редкая',9:'очень редкая'})[tier(c.l)];
}
function knownRecipes(){return ST.knownRecipes||['Зелье лечения 1.1']}
function knows(c){
  if(knownRecipes().includes(recipeKey(c)))return true;
  if(c.k==='eff'&&c.f&&c.l<10)return [2,5,7,9].filter(l=>l>tier(c.l)).some(l=>knownRecipes().includes(recipeKey({...c,l})));
  return false;
}
function supply(c,q=1){
  const deficits=[], warnings=[], M=+$('m').value||1;
  if(!knows(c))warnings.push('рецепт или ступень формулы не отмечены известными');
  if(c.l>M)warnings.push('выше текущего мастерства');
  if(c.l>(S.t.lab?10:$('anar').checked?8:5))warnings.push('нужно другое оборудование');
  const mat=ST.mat||{herbs:[],ess:[],cat:[],other:[]};
  const kind=c.b==='ядовитая'?'poison':'heal';
  const byValue=['chg','rea','fl','psn','oils'].includes(c.k);
  if(byValue){
    const want=q*(parseFloat(String(c.p).replace(/\s/g,'').replace(',','.'))||0)/3;
    const lack=Math.max(0,want-(mat.herbs.filter(h=>h.k===kind&&h.l>=c.l).reduce((s,h)=>s+h.q*HERB_P[h.l],0)+(mat.pools||[]).filter(p=>p.k===kind&&p.min>=c.l).reduce((s,p)=>s+p.v,0)+((!mat.pools&&c.l===1&&mat.pool?.[kind])||0)));
    if(lack>1e-8)deficits.push({n:KIND[kind]+' травы ур. '+c.l+'+ по ценности',q:lack,price:lack,value:true});
  }else{
    const lack=Math.max(0,c.l*q-herbCount(kind,c.l));
    if(lack)deficits.push({n:KIND[kind]+' травы ур. '+c.l,q:lack,price:lack*HERB_P[c.l]});
  }
  // Общий остаток: трофей с двумя типами нельзя потратить дважды.
  const stock=mat.ess.map(e=>({...e,q:essExpired(e)?0:e.q}));
  const needs=c.e?essParseAll(c).map(e=>({...e,q})):[];
  needs.sort((a,b)=>stock.filter(e=>essMatch(e,a.type)&&e.l>=a.l).length-stock.filter(e=>essMatch(e,b.type)&&e.l>=b.l).length);
  for(const need of needs){
    let left=need.q;
    const candidates=stock.filter(e=>essMatch(e,need.type)&&e.l>=need.l&&e.q>0).sort((a,b)=>a.types.length-b.types.length||a.l-b.l);
    for(const e of candidates){const take=Math.min(left,e.q);e.q-=take;left-=take;if(e.st==='bad'&&take)warnings.push('нестабильная эссенция: +2 к СЛ');}
    if(left>1e-8)deficits.push({n:'Эссенция '+need.type+' '+ROM[need.l],q:left,price:need.l<=6?left*HERB_P[need.l]:null});
  }
  if(c.l>=3){
    const order=ORD(c.l),cats=mat.cat.filter(x=>x.o===order),remaining=cats.reduce((s,x)=>s+Math.max(0,cmax(x)-x.used),0);
    const stable=cats.reduce((s,x)=>s+Math.max(0,stab(x)-x.used),0);
    if(remaining<q){const count=Math.ceil((q-remaining)/5);deficits.push({n:'Катализатор '+ROM[order]+' порядка'+(order===4?' — только изготовление из сюжетного сырья':''),q:count,price:order===4?null:[0,70,350,1750][order]*count});}
    else if(stable<q)warnings.push('потребуются проверки нестабильности катализатора');
  }
  if(c.cm){
    const have=mat.other.filter(o=>o.n.toLowerCase().includes(c.cm.k)).reduce((s,o)=>s+o.q,0),lack=Math.max(0,(c.cm.use?q:1)-have);
    if(lack)deficits.push({n:c.cm.t,q:lack,price:lack*c.cm.gp});
  }
  return {deficits,warnings,ready:knows(c)&&c.l<=M&&c.l<=(S.t.lab?10:$('anar').checked?8:5)&&!deficits.length};
}
let AV={mode:'known',selected:'Зелье лечения 1.1',q:1};
function renderAvailability(){
  const box=$('availability');if(!box||!ST.mat)return;
  const c=RECIPES.find(c=>c.n===AV.selected)||RECIPES[0],check=supply(c,AV.q);
  const filtered=RECIPES.filter(c=>AV.mode==='all'||AV.mode==='known'&&knows(c)||AV.mode==='ready'&&supply(c).ready);
  box.innerHTML=`<h2>Что могу сварить</h2><div class="row"><div><label class="f">Показать</label><select id="avMode"><option value="known">Известные рецепты</option><option value="ready">Есть материалы на одну попытку</option><option value="all">Все рецепты</option></select></div><div><label class="f">Рецепт</label><select id="avRecipe">${filtered.map(x=>`<option value="${esc(x.n)}">${esc(x.n)} · ${ROM[x.l]}</option>`).join('')}</select></div><div><label class="f">Доз / попыток</label><input id="avQty" type="number" min="1" max="100" value="${AV.q}"></div></div>
  <p class="note">Отметь известные рецепты или ступени формул здесь — названия записей журнала могут быть произвольными. Материалы считаются на каждую попытку, без предполагаемой экономии на удачных бросках.</p>
  ${!filtered.length?'<p class="note">Подходящих рецептов нет. Выбери «Все рецепты», чтобы отметить освоенное.</p>':''}
  <label class="tg"><input id="avKnown" type="checkbox" ${knows(c)?'checked':''}><span>Известно: ${esc(recipeKey(c))}</span></label>
  <p id="avWarnings" class="note">${check.warnings.map(esc).join(' · ')||'Мастерство и оборудование подходят.'}</p>
  <div id="avShopping">${check.deficits.length?'<b>Докупить:</b><ul>'+check.deficits.map(d=>`<li>${esc(d.n)} — ${fmtZ(d.q)}${d.value?' зм сырья':' шт.'}; ${d.price==null?'цена у мастера':fmtZ(d.price)+' зм'}</li>`).join('')+'</ul>':'Материалов хватает; списаний не было.'}</div>
  <p class="note">Докупка: <b>${fmtZ(check.deficits.reduce((s,d)=>s+(d.price||0),0))} зм</b>${check.deficits.some(d=>d.price==null)?' + позиции с ценой у мастера':''}; на руках ${fmtZ(ST.mat.gold||0)} зм. Цены справочные, наличие у продавца уточни.</p>
  <div class="btns"><button id="avCopy" type="button" class="btn soft">Скопировать докупку</button><button id="avOpen" type="button" class="btn">Перейти к варке</button></div>`;
  $('avMode').value=AV.mode;
  if(filtered.some(x=>x.n===c.n))$('avRecipe').value=c.n;
  else if(filtered.length){AV.selected=filtered[0].n;renderAvailability();return;}
  $('avKnown').disabled=!filtered.length||(knows(c)&&!knownRecipes().includes(recipeKey(c)));$('avOpen').disabled=!filtered.length;
  $('avMode').onchange=e=>{AV.mode=e.target.value;renderAvailability()};
  $('avRecipe').onchange=e=>{AV.selected=e.target.value;renderAvailability()};
  $('avQty').onchange=e=>{AV.q=Math.max(1,Math.min(100,+e.target.value||1));renderAvailability()};
  $('avKnown').onchange=e=>{const on=e.target.checked;mutate(()=>{const keys=knownRecipes().filter(k=>k!==recipeKey(c));if(on)keys.push(recipeKey(c));ST.knownRecipes=keys;logx('Известные рецепты: '+recipeKey(c)+' — '+(on?'да':'нет'))})};
  $('avCopy').onclick=async()=>{try{await navigator.clipboard.writeText('Докупка для '+c.n+' ×'+AV.q+'\n'+check.deficits.map(d=>`${d.n}: ${fmtZ(d.q)}${d.price==null?' — цена у мастера':' — '+fmtZ(d.price)+' зм'}`).join('\n'));$('avCopy').textContent='Скопировано'}catch(e){$('avCopy').textContent='Не скопировалось'}};
  $('avOpen').onclick=()=>{if(c.k==='basic'){tab('jour');const el=$('jrec');el.querySelector('.rn').value=c.n;el.querySelector('.rn').dispatchEvent(new Event('input'));el.scrollIntoView({block:'center'})}else{S.sel=D.indexOf(c);render();$('out').scrollIntoView({block:'center'})}};
}
['m','anar'].forEach(id=>$(id).addEventListener('change',renderAvailability));

function snapshot(){
  return {format:'alcemy-helper',version:1,created:new Date().toISOString(),state:JSON.parse(JSON.stringify(ST)),situation:{...S.t},tracks:JSON.parse(JSON.stringify(TR)),settings:Object.fromEntries(['m','b','anar','sel','tab','theme'].map(k=>[k,ls.get(k)]))};
}
let DL;  // в опубликованном помощнике — capability downloads; вне Claude — обычная ссылка
async function downloadSnapshot(data,prefix='alcemy-save'){
  const name=prefix+'-'+new Date().toISOString().slice(0,10)+'.json',text=JSON.stringify(data,null,2);
  if(DL===undefined)DL=window.claude&&window.claude.use?await window.claude.use('downloads').catch(()=>null):null;
  if(DL){try{await DL.save({filename:name,data:text});return true}catch(e){return false}}
  const url=URL.createObjectURL(new Blob([text],{type:'application/json'})),a=document.createElement('a');
  a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return true;
}
function validateSnapshot(data){
  const fail=()=>{throw Error('Неверный или повреждённый файл сохранения')};
  function inspect(x){if(!x||typeof x!=='object')return;for(const k of Object.keys(x)){if(['__proto__','constructor','prototype'].includes(k))fail();inspect(x[k]);}}
  inspect(data);
  if(data?.format!=='alcemy-helper'||data.version!==1||data.state?.v!==1||!Array.isArray(data.tracks)||!data.settings)fail();
  const s=data.state;
  if(data.situation&&(typeof data.situation!=='object'||Object.values(data.situation).some(v=>typeof v!=='boolean')))fail();
  for(const key of ['people','bag','ent','rests','r10','lrs','trig','log'])if(!Array.isArray(s[key]))fail();
  if(!Number.isFinite(s.T)||s.T<0||!s.people.length||!s.mat||!Number.isFinite(s.mat.gold)||s.mat.gold<0)fail();
  for(const key of ['rests','r10','lrs'])if(s[key].some(v=>!Number.isFinite(v)))fail();
  if(s.log.some(l=>typeof l.t!=='string'||!Number.isFinite(l.T)))fail();
  for(const e of s.ent)if(typeof e.n!=='string'||typeof e.who!=='string'||!Number.isFinite(e.t0)||!Number.isFinite(e.dur)||!Number.isFinite(e.tox))fail();
  for(const key of ['herbs','ess','cat','other'])if(!Array.isArray(s.mat[key]))fail();
  const ids=new Set();for(const p of s.people){if(typeof p.id!=='string'||typeof p.name!=='string'||!Number.isFinite(p.limit)||ids.has(p.id))fail();ids.add(p.id);}
  if(s.ent.some(e=>!ids.has(e.who)))fail();
  if(s.trig.some(t=>!t||!ids.has(t.who)||!Number.isFinite(t.T)))fail();
  if(s.plan&&(!Array.isArray(s.plan.items)||s.plan.items.some(i=>typeof i.n!=='string'||!ids.has(i.who)||!Number.isFinite(i.q)||i.q<0)))fail();
  if(s.hrs&&(!Number.isFinite(s.hrs.total)||!Array.isArray(s.hrs.log)||s.hrs.log.some(l=>typeof l.w!=='string'||!Number.isFinite(l.T)||!Number.isFinite(l.h))))fail();
  if(s.fight&&(!Array.isArray(s.fight.heals)||!Array.isArray(s.fight.coats)||!Array.isArray(s.fight.now)))fail();
  if(s.talis){const r=s.talis,n=x=>Number.isSafeInteger(x)&&x>=0;
    if(!n(r.hp)||r.hp>TALIS_LIMITS.hp||!n(r.temp)||!n(r.sp)||r.sp>TALIS_LIMITS.sp||!n(r.meta)||r.meta>TALIS_LIMITS.meta||
      !r.slots||![1,2].every(l=>n(r.slots[l]))||typeof r.concentration!=='string'||typeof r.reaction!=='boolean'||
      (r.dc!==null&&(!n(r.dc)||r.dc<10))||!n(r.lastDamage))fail();}
  for(const b of s.bag)if(typeof b.n!=='string'||!ids.has(b.who)||!Number.isFinite(b.q)||b.q<0)fail();
  for(const h of s.mat.herbs)if(!['heal','poison'].includes(h.k)||!Number.isInteger(h.l)||h.l<1||h.l>10||!Number.isFinite(h.q)||h.q<0)fail();
  for(const e of s.mat.ess)if(typeof e.id!=='string'||typeof e.n!=='string'||!Array.isArray(e.types)||e.types.some(t=>typeof t!=='string')||!Number.isInteger(e.l)||e.l<1||e.l>10||!Number.isFinite(e.q)||e.q<0)fail();
  for(const c of s.mat.cat)if(typeof c.id!=='string'||!Number.isInteger(c.o)||c.o<1||c.o>4||!Number.isFinite(c.used)||c.used<0)fail();
  for(const o of s.mat.other)if(typeof o.n!=='string'||!Number.isFinite(o.q)||o.q<0)fail();
  if(s.knownRecipes&&(!Array.isArray(s.knownRecipes)||s.knownRecipes.some(k=>typeof k!=='string')))fail();
  if(s.mat.pools&&(!Array.isArray(s.mat.pools)||s.mat.pools.some(p=>!['heal','poison'].includes(p.k)||!Number.isInteger(p.min)||p.min<1||p.min>10||!Number.isFinite(p.v)||p.v<0)))fail();
  for(const k of ['m','b','anar','sel','tab','theme'])if(data.settings[k]!=null&&typeof data.settings[k]!=='string')fail();
  if(data.settings.m!=null&&(!Number.isInteger(+data.settings.m)||+data.settings.m<1||+data.settings.m>10))fail();
  if(data.settings.b!=null&&(!Number.isFinite(+data.settings.b)||+data.settings.b< -5||+data.settings.b>30))fail();
  const tids=new Set();for(const t of data.tracks){if(typeof t.id!=='string'||!/^[\w-]+$/.test(t.id)||tids.has(t.id)||typeof t.name!=='string'||!Number.isFinite(t.current)||!Number.isFinite(t.target)||t.target<=0)fail();tids.add(t.id);}
  return data;
}
let PENDING_SAVE=null;
$('backupExport').onclick=async()=>{if(!JDB||JBUSY.size){$('backupStatus').textContent='Дождись загрузки и сохранения журнала.';return}$('backupStatus').textContent=await downloadSnapshot(snapshot())?'Сохранение скачано: сумки, материалы, журнал и настройки.':'Файл не сохранён.'};
$('backupImport').onclick=()=>{$('backupFile').value='';$('backupFile').click()};
$('backupFile').onchange=async e=>{
  try{const file=e.target.files[0];if(!file)return;if(file.size>5*1024*1024)throw Error('Файл больше 5 МБ');PENDING_SAVE=validateSnapshot(JSON.parse(await file.text()));
    const d=PENDING_SAVE;$('restoreSummary').textContent=`В файле: ${d.state.bag.length} позиций в сумках, ${d.tracks.length} записей журнала, ${fmtZ(d.state.mat.gold)} зм. ${DOC?'Обновится и общая база помощника.':'Восстановление в этом браузере.'}`;$('restoreDialog').showModal();
  }catch(err){PENDING_SAVE=null;$('backupStatus').textContent='Не восстановлено: '+err.message}
};
$('restoreCancel').onclick=()=>{PENDING_SAVE=null;$('restoreDialog').close()};
$('restoreDialog').oncancel=e=>{if($('restoreApply').disabled)e.preventDefault();else PENDING_SAVE=null};
$('restoreApply').onclick=async()=>{
  if(!PENDING_SAVE||!JDB||JBUSY.size){$('restoreSummary').textContent='Дождись загрузки и сохранения журнала.';return}
  const next=PENDING_SAVE,old=snapshot(),col=JDB.collection('tracks');$('restoreApply').disabled=true;$('restoreCancel').disabled=true;
  clearTimeout(saveT);
  if(!await downloadSnapshot(old,'alcemy-before-restore')){$('restoreSummary').textContent='Копия текущего состояния не сохранена — восстановление отменено.';$('restoreApply').disabled=false;$('restoreCancel').disabled=false;return}
  try{
    for(const t of next.tracks){const {id,...data}=t;await col.doc(id).set(data)}
    for(const t of old.tracks)if(!next.tracks.some(n=>n.id===t.id))await col.doc(t.id).delete();
    const restored=JSON.parse(JSON.stringify(next.state));restored.u=Date.now();
    // Сначала проверить запись браузера; только затем заменять общее состояние.
    localStorage.setItem('belt',JSON.stringify(restored));
    if(DOC){clearTimeout(saveT);await DOC.set({s:JSON.stringify(restored),u:restored.u})}
    ST=restored;TR=next.tracks;S.t={...(next.situation||{})};UNDO=[];UNDOJ={};
    for(const [key,value] of Object.entries(next.settings))if(['m','b','anar','sel','tab','theme'].includes(key)){if(value==null)localStorage.removeItem(key);else ls.set(key,String(value))}
    $('m').value=ls.get('m')||2;lastM=+$('m').value;$('b').value=ls.get('b')||4;$('anar').checked=ls.get('anar')==='1';
    if(ls.get('theme'))document.documentElement.dataset.theme=ls.get('theme');
    S.sel=D.findIndex(c=>c.n===ls.get('sel'));if(S.sel<0)S.sel=null;
    renderBelt();renderJournal();list();render();tab(['belt','jour','plan'].includes(ls.get('tab'))?ls.get('tab'):'brew');
    PENDING_SAVE=null;$('restoreDialog').close();$('backupStatus').textContent='Сохранение восстановлено.';
  }catch(err){
    let rolled=true;try{for(const t of old.tracks){const {id,...data}=t;await col.doc(id).set(data)}for(const t of next.tracks)if(!old.tracks.some(o=>o.id===t.id))await col.doc(t.id).delete();ST=old.state;TR=old.tracks;S.t={...old.situation};localStorage.setItem('belt',JSON.stringify(ST));if(DOC)await DOC.set({s:JSON.stringify(ST),u:Date.now()});renderBelt();renderJournal()}catch(e){rolled=false}
    $('restoreSummary').textContent='Не восстановлено: '+err.message+(rolled?'. Предыдущее состояние возвращено.':'. Откат не завершён: восстанови скачанную копию после восстановления связи.');
  }finally{$('restoreApply').disabled=false;$('restoreCancel').disabled=false}
};

// ===== Блоки для листа LSS: текст для ручного переноса (лист в LSS правит игрок) =====
const LSS_UNIT={marks:' отметок',count:' успехов'};
function lssLabel(t){
  let m=t.name.match(/^Формула «(.+?)».*цель (.+)$/);if(m)return `${m[1]} (${m[2]})`;
  m=t.name.match(/^Формула «(.+?)».*по образцу (.+)$/);if(m)return `${m[1]} (по образцу ${m[2]})`;
  m=t.name.match(/^Мастерство (\d+) → (\d+)$/);if(m)return `Рост мастерства ${m[1]} → ${m[2]}`;
  return t.name;
}
function lssBlocks(){
  const m=+$('m').value||1,out=[],tr=[...TR].sort((a,b)=>(a.order??99)-(b.order??99));
  // Этапы Корневой метки: только первый незавершённый, следующие ещё не начаты
  const open=tr.filter(t=>!t.done),firstRoot=open.find(t=>/^Корневая метка/.test(t.name));
  const prog=[`${m} уровень алхимии, +${MB(m)} к алхимии.`].concat(open.filter(t=>!/^Корневая метка/.test(t.name)||t===firstRoot)
    .map(t=>`${lssLabel(t)}: ${fmtZ(t.current)} из ${fmtZ(t.target)}${LSS_UNIT[t.mode]||''}.`));
  out.push({t:'Прогресс («2 уровень алхимии… Крепкого… чернила…») — заменить целиком',x:prog.join('\n')});
  const rec=tr.filter(t=>t.done&&/^(Рецепт|Формула)/.test(t.name)).map(t=>'Рецепт открыт: '+t.name.replace(/^Рецепт:\s*/,''));
  out.push({t:'Открытые рецепты («Рецепт открыт…») — заменить целиком',x:rec.join('\n')||'Открытых рецептов нет.'});
  const unit=n=>(SEED.items.find(i=>i.n===n)||{}).u,qty=(n,q)=>unit(n)?` (${q} ${unit(n)})`:q!==1?` ×${fmtZ(q)}`:'';
  const mine=ST.bag.filter(i=>i.who==='p1'&&i.q>0),line=i=>i.n+qty(i.n,i.q)+(i.note&&i.note!=='на разборку'?` (${i.note})`:'');
  const bag=['Зелья и расходники',...mine.filter(i=>i.note!=='на разборку').map(line),'','На разборку',...mine.filter(i=>i.note==='на разборку').map(line)];
  out.push({t:'Снаряжение: подразделы «Зелья и расходники» и «На разборку» — заменить',x:bag.join('\n')});
  const M=ST.mat||{herbs:[],ess:[],cat:[],other:[]};
  const ing=['Ингредиенты',...M.herbs.filter(h=>h.q>0).map(h=>`${KIND[h.k]||h.k} травы ${h.l} ур. ×${fmtZ(h.q)}`),
    ...M.ess.filter(e=>e.q>0).map(e=>`${e.n} (эссенция ${e.types.join(' / ')} ${ROM[e.l]})${e.q!==1?' ×'+fmtZ(e.q):''}`),
    ...M.cat.map(c=>`Катализатор ${ROM[c.o]} порядка — применений ${c.used} из ${cmax(c)}`),
    ...M.other.filter(o=>o.q>0).map(o=>o.n+(o.q!==1?' ×'+fmtZ(o.q):''))];
  out.push({t:'Снаряжение: подраздел «Ингредиенты» — заменить',x:ing.join('\n')});
  out.push({t:'Монеты — сверить сумму',x:`Всего ${fmtZ(M.gold||0)} зм. Раздели на зм, см и мм как удобно: 1 зм = 10 см = 100 мм.`});
  return out;
}
$('lssOpen').onclick=()=>{
  if(!JDB||!ST.mat){$('backupStatus').textContent='Дождись загрузки сумки и журнала.';return}
  const box=$('lssBody');box.innerHTML='';
  lssBlocks().forEach(b=>{const d=document.createElement('div');d.className='lb';
    d.innerHTML=`<h3>${esc(b.t)}</h3><textarea readonly aria-label="${esc(b.t)}"></textarea><button type="button" class="btn sm soft">Скопировать</button>`;
    const ta=d.querySelector('textarea'),bt=d.querySelector('button');ta.value=b.x;ta.rows=Math.min(14,b.x.split('\n').length+1);
    bt.onclick=async()=>{try{await navigator.clipboard.writeText(b.x);bt.textContent='Скопировано'}catch(e){ta.select();bt.textContent='Выделено — скопируй вручную'}setTimeout(()=>bt.textContent='Скопировать',1600)};
    box.appendChild(d)});
  $('lssDialog').showModal();
};
$('lssClose').onclick=()=>$('lssDialog').close();

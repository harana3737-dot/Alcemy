// План сочетаний: проверка не расходует предметы и не меняет действующие эффекты.
let COMBO={who:'p1',catalog:false,items:[],concentration:''};
try{const saved=JSON.parse(ls.get('combo')||'null');if(saved&&Array.isArray(saved.items))COMBO={...COMBO,...saved,items:saved.items.filter(x=>x&&typeof x.n==='string').slice(0,5).map(x=>({...x,n:x.n,q:Math.max(1,Math.min(5,Math.floor(+x.q||1)))}))}}catch(e){}
// Та же арифметика флакона используется в форме фактического выпивания.
function flaskProfile(c,mods={},variant=0){
  const variants=toxVars(c),v=variants[Math.max(0,Math.min(variants.length-1,Math.floor(+variant||0)))];
  const charge=isChg(c),base=durMin(c.d);
  let duration=charge?(mods.short?10:mods.lwin?240:60):base;
  if(!charge){if(mods.long)duration=Math.min(Math.round(base*1.5),base+60);if(mods.dbl)duration=Math.min(base*2,base+480);if(mods.short)duration=Math.round(duration/2)}
  return {variant:v.v,tox:v.t+(mods.heavy?1:0),duration,uses:charge&&mods.twin?2:1,clean:!charge&&!!mods.clean};
}
const FLASK_NAMES={'Долгое действие':'long','Двойной срок':'dbl','Чистый':'clean','Долгое окно':'lwin','Двойной заряд':'twin','дефект: Короткое':'short','дефект: Тяжёлое':'heavy'};
function flaskNote(note){const mods={};String(note||'').split(' + ').forEach(x=>{if(FLASK_NAMES[x.trim()])mods[FLASK_NAMES[x.trim()]]=true});return mods}
const COMBO_KITS={
  'Защита':['Доспехи мага','Щит веры'],
  'Разведка':['Видение невидимого','Паук'],
  'Урон и реакция':['Психическая плеть','Щит']
};
function comboMatches(c){return (!COMBO.search||c.n.toLocaleLowerCase('ru').includes(COMBO.search.toLocaleLowerCase('ru')))&&(!COMBO.filter||COMBO.filter==='soft'&&toxVars(c).some(v=>v.t===0)||COMBO.filter==='alchemy'&&c.a||COMBO.filter==='normal'&&c.cc||COMBO.filter==='none'&&!c.a&&!c.cc)}
function checkCombo(items,context){
  const rows=items.map(item=>{
    const c=byName(item.n),q=Math.max(1,Math.min(5,Math.floor(+item.q||1)));
    const profile=c&&flaskProfile(c,item.mods||{},item.variant);if(profile)profile.other=item.other||[];return c&&DRINK(c)?{c,q,profile,note:item.note||'',tox:profile.tox*q}:null;
  }).filter(Boolean);
  const warnings=[],alchemy=[...(context.alchemy||[])],normal=[];
  const names=new Set(context.names||[]);
  for(const row of rows){
    if(row.c.a)alchemy.push(...Array(row.q).fill(row.c.n));
    if(row.c.cc)normal.push(...Array(row.q).fill(row.c.n));
    if(!isChg(row.c)&&(names.has(row.c.n)||row.q>1))warnings.push(`«${row.c.n}»: одноимённые эффекты не складываются, токсичность каждой дозы сохраняется.`);
    names.add(row.c.n);
  }
  if(alchemy.length>1)warnings.push(`Алхимическая концентрация: одновременно один эффект. Новый прекратит предыдущий: ${alchemy.join(' → ')}.`);
  const concentration=(context.concentration||'').trim();
  if(normal.length+(concentration?1:0)>1)warnings.push(`Обычная концентрация: одновременно один эффект. После применения заряда прежний прекратится: ${[concentration,...normal].filter(Boolean).join(' → ')}.`);
  for(const item of items){const qualities=Object.entries(item.mods||{}).filter(([k,v])=>v&&['long','dbl','clean','lwin','twin'].includes(k)).length+(item.other||[]).length;if(qualities>2||qualities>1&&(item.mods?.dbl||item.mods?.twin||(item.other||[]).some(n=>['Крепкая привязка','Полное усиление'].includes(n))))warnings.push('Качество одного флакона: натуральная 20 даёт один бонус 20 либо два разных бонуса 5+; проверь выбранное сочетание бонусов.');if((item.other||[]).includes('Сильная привязка')&&(item.other||[]).includes('Крепкая привязка'))warnings.push('Привязка одного флакона: выбери +1 или +2; вместе они не складываются.')}
  const added=rows.reduce((sum,row)=>sum+row.tox,0),total=context.tox+added,excess=Math.max(0,total-context.limit);
  if(excess&&added)warnings.push(`Передозировка: превышение ${excess}, спасбросок Телосложения СЛ ${10+2*excess}. При провале — интоксикация и ${excess}к6 урона без типа${excess>=3?', также 1 истощение':''}.`);
  else if(excess)warnings.push('Текущая токсичность уже выше предела; план не добавляет токсичности.');
  return {rows,added,total,excess,warnings};
}
function comboStock(pid){
  const stock=new Map();
  for(const b of myBag(pid)){const c=bagCard(b);if(c&&DRINK(c)&&b.q>0)stock.set(c.n,(stock.get(c.n)||0)+b.q)}
  return stock;
}
function renderCombo(){
  if($('tab-combo').hidden)return;
  if(!P(COMBO.who))COMBO.who=ST.people[0]?.id;
  const p=P(COMBO.who);if(!p)return;
  $('comboSearch').value=COMBO.search||'';$('comboFilter').value=COMBO.filter||'';
  const stock=comboStock(p.id),options=D.filter(c=>DRINK(c)&&(COMBO.catalog||stock.has(c.n))&&comboMatches(c)).sort((a,b)=>a.n.localeCompare(b.n,'ru'));
  $('comboWho').innerHTML=ST.people.map(x=>`<option value="${esc(x.id)}">${esc(x.name)}</option>`).join('');$('comboWho').value=p.id;
  $('comboCatalog').checked=!!COMBO.catalog;
  $('comboConcentration').value=p.id==='p1'?(ST.talis?.concentration||COMBO.concentration):COMBO.concentration;
  $('comboConcentration').readOnly=p.id==='p1'&&!!ST.talis?.concentration;
  const root=$('comboItems');root.innerHTML='';
  COMBO.items.forEach((item,index)=>{
    const row=document.createElement('div');row.className='row combo-row';
    const missing=!options.some(c=>c.n===item.n);
    row.innerHTML=`<div><label class="f">Эликсир ${index+1}</label><select class="combo-name" aria-label="Эликсир ${index+1}">${missing?`<option value="${esc(item.n)}">${esc(item.n)} — вне фильтра или нет в сумке</option>`:''}${options.map(c=>`<option value="${esc(c.n)}">${esc(c.n)}${COMBO.catalog?'':' · '+stock.get(c.n)+' доз'}</option>`).join('')}</select></div><div style="flex:0 0 70px"><label class="f">Доз</label><input class="combo-qty" aria-label="Доз ${index+1}" type="number" min="1" max="5" value="${item.q}"></div><button type="button" class="btn ghost combo-remove" aria-label="Убрать эликсир ${index+1}">Убрать</button>`;
    row.querySelector('select').value=item.n;
    row.querySelector('select').onchange=e=>{COMBO.items[index]={n:e.target.value,q:item.q};saveCombo()};
    row.querySelector('input').onchange=e=>{COMBO.items[index].q=Math.max(1,Math.min(5,Math.floor(+e.target.value||1)));saveCombo()};
    row.querySelector('button').onclick=()=>{COMBO.items.splice(index,1);saveCombo()};root.appendChild(row);
    const c=byName(item.n);if(!c)return;
    const extras=document.createElement('div');extras.className='card';extras.style.marginBottom='12px';
    const bottles=myBag(p.id).filter(b=>bagCard(b)===c&&b.q>0);
    extras.innerHTML=`<label class="f">Флакон из сумки / сценарий</label><select class="combo-bottle"><option value="">Сценарий: бонусы задаются вручную</option>${bottles.map(b=>`<option value="${esc(b.note||'') || '__plain__'}">${esc(b.note||'Обычный')} · ${b.q} доз</option>`).join('')}</select><label class="f">Вариант токсичности</label><select class="combo-variant">${toxVars(c).map((v,i)=>`<option value="${i}">${esc(v.v)} · ${v.t}</option>`).join('')}</select><div class="toggles">${MODS[isChg(c)?'chg':'eff'].filter(m=>isChg(c)||durMin(c.d)>0||!['long','dbl','short'].includes(m[0])).map(([id,n,h])=>`<label class="tg"><input type="checkbox" data-mod="${id}" ${item.mods?.[id]?'checked':''}><span>${esc(n)}<small>${esc(h)}</small></span></label>`).join('')}</div><p class="note">5+: ${esc(c.b5)}. Нат. 20: ${esc(c.b20)}. Бонусы к СЛ, кубам и целям применяются по карточке; продление ограниченного ресурса не добавляет применений.</p>`;
    const special=document.createElement('div');special.className='toggles';
    const basicNames=new Set(MODS[isChg(c)?'chg':'eff'].map(x=>x[1]));
    const qualities=bonusLists(c.n,c.l,c),other=[...qualities.L5,...qualities.L20].filter(n=>!KEEP_OFF.has(n)&&!basicNames.has(n));
    special.innerHTML=other.map(n=>`<label class="tg"><input type="checkbox" data-quality="${esc(n)}" ${(item.other||[]).includes(n)?'checked':''}><span>${esc(n)}</span></label>`).join('');
    special.querySelectorAll('input').forEach(el=>el.onchange=()=>{item.other=(item.other||[]).filter(n=>n!==el.dataset.quality);if(el.checked)item.other.push(el.dataset.quality);delete item.note;saveCombo()});extras.appendChild(special);
    extras.querySelector('.combo-bottle').value=item.note===undefined?'':item.note||'__plain__';
    extras.querySelector('.combo-bottle').onchange=e=>{if(!e.target.value){delete item.note}else{item.note=e.target.value==='__plain__'?'':e.target.value;item.mods=flaskNote(item.note);item.other=item.note.split(' + ').filter(n=>other.includes(n));const variant=toxVars(c).findIndex(v=>v.v!=='основной'&&item.note.includes(v.v));item.variant=Math.max(0,variant)}saveCombo()};
    extras.querySelector('.combo-variant').value=item.variant||0;
    extras.querySelector('.combo-variant').onchange=e=>{item.variant=+e.target.value;saveCombo()};
    extras.querySelectorAll('[data-mod]').forEach(el=>el.onchange=()=>{item.mods={...item.mods,[el.dataset.mod]:el.checked};delete item.note;if(el.checked&&el.dataset.mod==='long')item.mods.dbl=false;if(el.checked&&el.dataset.mod==='dbl')item.mods.long=false;saveCombo()});root.appendChild(extras);
  });
  const result=checkCombo(COMBO.items,{tox:toxOfP(p.id),limit:p.limit,
    alchemy:ST.ent.filter(e=>e.who===p.id&&e.a&&isActive(e)).map(e=>e.n),
    names:ST.ent.filter(e=>e.who===p.id&&isActive(e)&&e.k==='eff').map(e=>e.n),
    concentration:$('comboConcentration').value});
  const stockWarnings=[];
  const requested=new Map();
  for(const item of COMBO.items){const key=JSON.stringify([item.n,item.note??null]);requested.set(key,(requested.get(key)||0)+item.q)}

  for(const [key,q] of requested){const [name,note]=JSON.parse(key);if(note===null)continue;const have=myBag(p.id).filter(b=>bagCard(b)?.n===name&&(b.note||'')===note).reduce((s,b)=>s+b.q,0);if(q>have)stockWarnings.push(`«${name}» (${note||'обычный'}): не хватает ${q-have} доз с этой пометкой.`)}
  const all=new Map();for(const item of COMBO.items)all.set(item.n,(all.get(item.n)||0)+item.q);
  for(const [name,q] of all){const lack=q-(stock.get(name)||0);if(lack>0)stockWarnings.push(`«${name}»: не хватает ${lack} доз в сумке.`)}
  const warnings=[...result.warnings,...stockWarnings];
  $('comboResult').innerHTML=`<p><b>Токсичность: ${toxOfP(p.id)} + ${result.added} = ${result.total} из ${p.limit}</b>${result.excess?' · превышение '+result.excess:' · запас '+(p.limit-result.total)}</p>
    ${warnings.length?'<ul class="combo-warnings">'+warnings.map(w=>`<li>${esc(w)}</li>`).join('')+'</ul>':'<p>Конфликтов концентрации и превышения токсичности по выбранному плану нет.</p>'}
    ${result.rows.map(r=>`<details><summary>${esc(r.c.n)} ×${r.q} · токсичность ${r.tox} · ${r.c.a?'алхимическая концентрация':r.c.cc?'обычная концентрация после применения':'без концентрации'}</summary><p>${esc(r.note)}${r.note?'<br>':''}${r.profile.variant!=='основной'?esc(r.profile.variant)+' · ':''}${isChg(r.c)?'Окно':'Длительность'}: ${r.profile.duration} мин${/\dк\d/.test(r.c.d)&&!isChg(r.c)?' (максимум; фактически брось кубы)':''}${isChg(r.c)?' · применений на флакон: '+r.profile.uses:''}. ${r.profile.clean?'Остаточная токсичность снимается 10 минутами отдыха после конца эффекта.':'Остаточная токсичность — до короткого отдыха.'}</p><p>${r.profile.other.map(n=>esc(n)+(n==='Сильная привязка'?' — +1 к табличной СЛ / атаке; свои заклинательные значения не повышает':n==='Крепкая привязка'?' — +2 к табличной СЛ / атаке; свои заклинательные значения не повышает':n==='Усиленное заклинание'?' — кубы как ячейкой на уровень выше; цели и длительность не меняются':n==='Полное усиление'?' — как ячейкой на уровень выше, по строке усиления исходного заклинания':n==='Лёгкий глоток'?' — влить союзнику бонусным действием':'' )).join('<br>')}</p><p>${esc(r.c.eff)}</p></details>`).join('')}`;
  $('comboAdd').disabled=COMBO.items.length>=5||!options.length;
  $('comboAdd').onclick=()=>{COMBO.items.push({n:options[0].n,q:1});saveCombo()};
}
$('comboKit').innerHTML='<option value="">Выбрать комплект…</option>'+Object.keys(COMBO_KITS).map(n=>`<option>${esc(n)}</option>`).join('');
$('comboKit').onchange=e=>{const kit=COMBO_KITS[e.target.value];if(kit){COMBO.items=kit.filter(n=>byName(n)).map(n=>({n,q:1}));COMBO.catalog=true;COMBO.search='';COMBO.filter='';$('comboSearch').value='';$('comboFilter').value='';saveCombo()}};
$('comboSearch').value=COMBO.search||'';$('comboSearch').oninput=e=>{COMBO.search=e.target.value;saveCombo()};
$('comboFilter').value=COMBO.filter||'';$('comboFilter').onchange=e=>{COMBO.filter=e.target.value;saveCombo()};
function saveCombo(){ls.set('combo',JSON.stringify(COMBO));renderCombo()}
$('comboWho').onchange=e=>{COMBO.who=e.target.value;COMBO.concentration='';saveCombo()};
$('comboCatalog').onchange=e=>{COMBO.catalog=e.target.checked;saveCombo()};
$('comboConcentration').onchange=e=>{COMBO.concentration=e.target.value.trim();saveCombo()};
$('comboClear').onclick=()=>{COMBO.items=[];saveCombo()};

function renderActiveBrews(){
  const box=$('activeBrews');if(!box||$('tab-brew').hidden)return;
  const list=ST.vol||[];box.hidden=!list.length;
  box.innerHTML=list.length?`<b>Незавершённые варки: ${list.length}</b><ul>${list.map(v=>`<li>${esc(v.n)}: ${fmtZ(v.prog)} / ${v.volume}${volIdle(v).ruined?' — испорчена':v.prog>=v.volume?' — готова к завершающей проверке':''}</li>`).join('')}</ul><button type="button" class="btn soft" id="openActiveBrews">Открыть в журнале</button>`:'';
  if(list.length)$('openActiveBrews').onclick=()=>{tab('jour');$('jvol').scrollIntoView({block:'start'})};
}

// План сочетаний: проверка не расходует предметы и не меняет действующие эффекты.
let COMBO={who:'p1',catalog:false,items:[],concentration:''};
try{const saved=JSON.parse(ls.get('combo')||'null');if(saved&&Array.isArray(saved.items))COMBO={...COMBO,...saved,items:saved.items.filter(x=>x&&typeof x.n==='string').slice(0,5).map(x=>({n:x.n,q:Math.max(1,Math.min(5,Math.floor(+x.q||1)))}))}}catch(e){}
function checkCombo(items,context){
  const rows=items.map(item=>{
    const c=byName(item.n),q=Math.max(1,Math.min(5,Math.floor(+item.q||1)));
    return c&&DRINK(c)?{c,q,tox:toxVars(c)[0].t*q}:null;
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
  const stock=comboStock(p.id),options=D.filter(c=>DRINK(c)&&(COMBO.catalog||stock.has(c.n))).sort((a,b)=>a.n.localeCompare(b.n,'ru'));
  $('comboWho').innerHTML=ST.people.map(x=>`<option value="${esc(x.id)}">${esc(x.name)}</option>`).join('');$('comboWho').value=p.id;
  $('comboCatalog').checked=!!COMBO.catalog;
  $('comboConcentration').value=p.id==='p1'?(ST.talis?.concentration||COMBO.concentration):COMBO.concentration;
  $('comboConcentration').readOnly=p.id==='p1'&&!!ST.talis?.concentration;
  const root=$('comboItems');root.innerHTML='';
  COMBO.items.forEach((item,index)=>{
    const row=document.createElement('div');row.className='row combo-row';
    const missing=!options.some(c=>c.n===item.n);
    row.innerHTML=`<div><label class="f">Эликсир ${index+1}</label><select class="combo-name" aria-label="Эликсир ${index+1}">${missing?`<option value="${esc(item.n)}">${esc(item.n)} — нет в выбранной сумке</option>`:''}${options.map(c=>`<option value="${esc(c.n)}">${esc(c.n)}${COMBO.catalog?'':' · '+stock.get(c.n)+' доз'}</option>`).join('')}</select></div><div style="flex:0 0 70px"><label class="f">Доз</label><input class="combo-qty" aria-label="Доз ${index+1}" type="number" min="1" max="5" value="${item.q}"></div><button type="button" class="btn ghost combo-remove" aria-label="Убрать эликсир ${index+1}">Убрать</button>`;
    row.querySelector('select').value=item.n;
    row.querySelector('select').onchange=e=>{COMBO.items[index].n=e.target.value;saveCombo()};
    row.querySelector('input').onchange=e=>{COMBO.items[index].q=Math.max(1,Math.min(5,Math.floor(+e.target.value||1)));saveCombo()};
    row.querySelector('button').onclick=()=>{COMBO.items.splice(index,1);saveCombo()};root.appendChild(row);
  });
  const result=checkCombo(COMBO.items,{tox:toxOfP(p.id),limit:p.limit,
    alchemy:ST.ent.filter(e=>e.who===p.id&&e.a&&isActive(e)).map(e=>e.n),
    names:ST.ent.filter(e=>e.who===p.id&&isActive(e)&&e.k==='eff').map(e=>e.n),
    concentration:$('comboConcentration').value});
  const stockWarnings=[];
  for(const [name,q] of COMBO.items.reduce((m,x)=>m.set(x.n,(m.get(x.n)||0)+x.q),new Map())){
    const lack=q-(stock.get(name)||0);if(lack>0)stockWarnings.push(`«${name}»: не хватает ${lack} доз в сумке.`);
  }
  const warnings=[...result.warnings,...stockWarnings];
  $('comboResult').innerHTML=`<p><b>Токсичность: ${toxOfP(p.id)} + ${result.added} = ${result.total} из ${p.limit}</b>${result.excess?' · превышение '+result.excess:' · запас '+(p.limit-result.total)}</p>
    ${warnings.length?'<ul class="combo-warnings">'+warnings.map(w=>`<li>${esc(w)}</li>`).join('')+'</ul>':'<p>Конфликтов концентрации и превышения токсичности по выбранному плану нет.</p>'}
    ${result.rows.map(r=>`<details><summary>${esc(r.c.n)} ×${r.q} · токсичность ${r.tox} · ${r.c.a?'алхимическая концентрация':r.c.cc?'обычная концентрация после применения':'без концентрации'}</summary><p>${esc(r.c.eff)}</p></details>`).join('')}`;
  $('comboAdd').disabled=COMBO.items.length>=5||!options.length;
  $('comboAdd').onclick=()=>{COMBO.items.push({n:options[0].n,q:1});saveCombo()};
}
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

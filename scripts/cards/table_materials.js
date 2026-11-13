// ===== Материалы Талиса: травы, эссенции, катализаторы; расход при записи варки =====
const HERB_P=__RULE_HERB__;
const ORD=l=>l<=2?0:l<=5?1:l<=7?2:l<=9?3:4;
const KIND={heal:'Лечебные',poison:'Ядовитые',any:'Любые'};
const fmtZ=v=>(Math.round(v*100)/100).toString().replace('.',',');
// Два старых имени относятся к одной подтверждённой порции. Отсутствующее сырьё не выдаётся.
function migrateHeldShadow(mat){
  if(!mat)return false;
  const isShadow=e=>['сгусток удержанной тени','эктоплазма полтергейста'].includes(String(e.n||'').trim().toLowerCase());
  const old=mat.other.filter(e=>isShadow(e)&&e.q===1);
  if(!old.length)return false;
  let present=mat.ess.find(e=>e.n==='Сгусток удержанной тени')||mat.ess.find(isShadow);
  if(!present){
    present={id:'held-shadow-20261112',n:'Сгусток удержанной тени',types:['Покров','Смерть/душа'],l:2,q:1,st:'fresh',note:'эссенция полтергейста; одна порция; не переработан; без консервации; в закрытой колбе не развеивается; переработка 1 час, СЛ 12'};
    mat.ess.push(present);
  }else if(present.n!=='Сгусток удержанной тени'){
    present.n='Сгусток удержанной тени';present.types=['Покров','Смерть/душа'];present.l=2;
  }
  mat.other=mat.other.filter(e=>!old.includes(e));
  return true;
}
// Разовое исправление неполного старого снимка, подтверждённое игроком 12.11.
// Метка сохраняется вместе с материалами: последующий расход/удаление не отменяется.
function restoreConfirmedSpark(mat){
  if(!mat||mat.sparkConfirmed20261112===true)return 0;
  mat.sparkConfirmed20261112=true;
  const name='Искра заблудшей души';
  if([...mat.other,...mat.ess].some(e=>e.n===name))return 1;
  mat.other.push({n:name,q:1,note:'эссенция блуждающего огонька; для определения нужна проверка; тип, ранг и СЛ неизвестны; количество порций не указано'});
  return 2;
}
function matInit(){if(ST.dayOff===undefined)ST.dayOff=13;if(!ST.mat||ST.matSeed===undefined){ST.mat=JSON.parse(JSON.stringify(SEED.mat));ST.matSeed=SEED.mid;return true}
  let ch=false;if(ST.mat.gold===undefined){ST.mat.gold=SEED.mat.gold;ch=true}
  if(migrateHeldShadow(ST.mat)){logx('Уточнение учёта: Сгусток удержанной тени — в эссенциях, одна порция, не переработан');ch=true;}
  const sparkFix=restoreConfirmedSpark(ST.mat);if(sparkFix){ch=true;if(sparkFix===2)logx('Исправлен неполный старый снимок: восстановлена запись Искры заблудшей души; тип и число порций не назначены');}
  if(ST.dayOff===undefined){ST.dayOff=13;ch=true}
  ST.mat.ess.forEach(e=>{if(e.id==='e4'&&!e.st){e.st='fresh';ch=true}});
  ST.mat.cat.forEach(x=>{if(!x.stable){x.stable=CAT_STABLE;ch=true}});return ch}
function essParseAll(c){const parts=String(c.e).split(' + ');const first=essParse({e:parts[0],l:c.l});
  return [first,...parts.slice(1).map(x=>{const p=essParse({e:x,l:first.l});if(!/\s(X|IX|VIII|VII|VI|V|IV|III|II|I)\b/.test(x))p.l=first.l;return p})]}
function essParse(c){const m=String(c.e).match(/^(.*?)\s+(X|IX|VIII|VII|VI|V|IV|III|II|I)\b/);return m?{type:m[1],l:ROM.indexOf(m[2])}:{type:String(c.e),l:c.l}}
const essMatch=(it,type)=>it.types.some(t=>t===type||type.startsWith(t)||t.startsWith(type));
// смешанные травы на сумму: [{k, min, v}] — годятся для предметов уровня ≤ min (Ж-85: чернила — правило мастера, заряды и склянки — по аналогии)
const pools=()=>{if(!ST.mat.pools){ST.mat.pools=[];const o=ST.mat.pool||{};['heal','poison'].forEach(k=>{if(o[k])ST.mat.pools.push({k,min:1,v:o[k]})});delete ST.mat.pool}return ST.mat.pools};
function herbValue(kind,minL=1){if(kind==='any')return herbValue('heal',minL)+herbValue('poison',minL);return ST.mat.herbs.filter(h=>h.k===kind&&h.l>=minL).reduce((s,h)=>s+h.q*HERB_P[h.l],0)+pools().filter(p=>p.k===kind&&p.min>=minL).reduce((s,p)=>s+p.v,0)}
function herbCount(kind,lvl){return ST.mat.herbs.filter(h=>h.k===kind&&h.l===lvl).reduce((s,h)=>s+h.q,0)}
// по ценности: сначала смешанные (от ближнего уровня), потом поштучные от дешёвых; от травы можно взять часть
function takeValue(kind,need,minL=1){
  if(kind==='any'){const h=Math.min(need,herbValue('heal',minL));const a=h>1e-9?'лечебные: '+takeValue('heal',h,minL):'';const b=need-h>1e-9?'ядовитые: '+takeValue('poison',need-h,minL):'';return [a,b].filter(Boolean).join('; ')}
  const used=[];
  pools().filter(p=>p.k===kind&&p.min>=minL&&p.v>0).sort((a,b)=>a.min-b.min).forEach(p=>{if(need<=1e-9)return;const t=Math.min(p.v,need);p.v=+(p.v-t).toFixed(2);need-=t;used.push(`смешанные от ур. ${p.min} −${fmtZ(+t.toFixed(2))} зм`)});
  ST.mat.pools=pools().filter(p=>p.v>1e-9);
  ST.mat.herbs.filter(h=>h.k===kind&&h.l>=minL&&h.q>0).sort((a,b)=>a.l-b.l).forEach(h=>{if(need<=1e-9)return;
    const t=Math.min(h.q,need/HERB_P[h.l]);h.q=+(h.q-t).toFixed(4);need-=t*HERB_P[h.l];used.push(`ур. ${h.l} −${fmtZ(+t.toFixed(2))}`)});
  ST.mat.herbs=ST.mat.herbs.filter(h=>h.q>1e-9);
  return used.join(', ');
}
// по числу (справочник «Травы»): N трав уровня предмета
function takeCount(kind,need,minL){
  const used=[];
  ST.mat.herbs.filter(h=>h.k===kind&&h.l===minL&&h.q>0).sort((a,b)=>a.l-b.l).forEach(h=>{if(need<=1e-9)return;const t=Math.min(h.q,need);h.q=+(h.q-t).toFixed(4);need-=t;used.push(`ур. ${h.l} −${fmtZ(+t.toFixed(2))}`)});
  ST.mat.herbs=ST.mat.herbs.filter(h=>h.q>1e-9);
  return used.join(', ');
}
function savedCount(box){let n=0;box.querySelectorAll('.b5s').forEach(s=>{if(s.value==='Экономия трав')n++});
  box.querySelectorAll('.b20s').forEach(s=>{if(s.value==='Два бонуса'){const r=s.parentNode;if([r.querySelector('.tw1').value,r.querySelector('.tw2').value].includes('Экономия трав'))n++}});return n}
function planUse(n,lvl,c,k,box){
  const att=k.n20+k.hi+k.ok+k.un+k.fl;if(!att||!ST.mat)return null;
  const saved=Math.min(att,savedCount(box));
  const kind=c?(c.b==='ядовитая'?'poison':'heal'):(potKind(n)==='poison'?'poison':'heal');
  const byValue=!!c&&['chg','psn','rea','fl','oils'].includes(c.k);
  const P={att,kind,saved,byValue,lvl};
  if(byValue){const v=parseFloat(String(c.p).replace(/\s/g,'').replace(',','.'))||0;P.value=Math.max(0,att-saved/2)*v/3}
  else P.herbs={l:lvl,q:Math.max(0,att-saved)*lvl};
  if(c)P.ess=essParseAll(c).map(e=>({...e,q:att}));
  if(lvl>=3)P.cat={o:ORD(lvl),q:att};
  if(c&&c.cm)P.cm={...c.cm,q:att};
  return P;
}
function resArea(box,n,lvl,c,k){
  const ar=box.querySelector('.rres');if(!ar)return;
  const keep={};ar.querySelectorAll('select').forEach(x=>keep[x.className]=x.value);
  const P=planUse(n,lvl,c,k,box);box._plan=P;if(!P){ar.innerHTML='';return}
  const rows=[];
  if(P.herbs){const have=herbCount(P.kind,P.herbs.l);
    rows.push(`${KIND[P.kind]} травы ур. ${P.herbs.l}: <b>${P.herbs.q}</b> из ${fmtZ(have)}${have<P.herbs.q?' <span class="bad">не хватает</span>':''}${P.saved?` <small>(экономия трав на ${P.saved})</small>`:''}`)}
  else{const have=herbValue(P.kind,P.lvl);rows.push(`${KIND[P.kind]} травы ур. ${P.lvl}+ на <b>${fmtZ(P.value)} зм</b> из ${fmtZ(have)} (по ценности, ⅓ цены)${have<P.value?' <span class="bad">не хватает</span>':''}${P.saved?` <small>(экономия на ${P.saved} — половина)</small>`:''}`)}
  if(P.ess)P.ess.forEach((E,ei)=>{const opts=ST.mat.ess.filter(e=>e.q>0).sort((a,b)=>(essMatch(b,E.type)-essMatch(a,E.type))||(a.l-b.l));
    const fit=opts.filter(e=>essMatch(e,E.type)&&e.l>=E.l), def=fit.find(e=>e.q>=P.att)||fit[0];
    rows.push(`Эссенция ${esc(E.type)} ${ROM[E.l]||''} ×${P.att}: <select class="res-e res-e${ei}" aria-label="Эссенция">${opts.map(e=>`<option value="${e.id}" ${def&&e.id===def.id?'selected':''}>${esc(e.n)} — ${e.types.map(esc).join(' / ')} ${ROM[e.l]} (${e.q})</option>`).join('')}<option value="" ${def?'':'selected'}>не списывать</option></select>${!def?' <span class="bad">подходящей нет</span>':def.q<P.att?` <span class="bad">есть только ${def.q}</span>`:''}${def&&def.l>E.l?' <small>(эссенция выше уровня)</small>':''}${def&&def.st==='good'?' <small>(отличная: +1 к проверке)</small>':''}${def&&def.st==='bad'?' <span class="wr">нестабильная: +2 к СЛ</span>':''}${def&&essExpired(def)?' <span class="bad">просрочена — только с разрешения мастера</span>':''}`)})
  if(P.cat){const opts=ST.mat.cat.filter(x=>x.o===P.cat.o&&x.used<cmax(x));const def=opts[0];
    let w='';if(def){const from=def.used+1,to=def.used+P.att;if(to>cmax(def))w=' <span class="bad">не хватит применений</span>';else if(to>stab(def)){const f=Math.max(stab(def)+1,from);w=` <span class="wr">применения ${f}–${to}: проверки нестабильности, СЛ ${instDC(def,f)}${to>f?'–'+instDC(def,to):''} (5.2)</span>`}}
    rows.push(`Катализатор ${ROM[P.cat.o]} порядка ×${P.att}: <select class="res-c" aria-label="Катализатор">${opts.map(x=>`<option value="${x.id}">${ROM[x.o]} порядка — ${x.used}/${cmax(x)}</option>`).join('')}<option value="" ${def?'':'selected'}>не списывать</option></select>${def?w:' <span class="bad">нет катализатора</span>'}${def&&def.used+P.att>stab(def)?'<label class="tg" style="padding:4px 0 0"><input type="checkbox" class="res-crack"><span>Проверка нестабильности провалена — катализатор треснул (доза испорчена; дозы после неё не варились — убери их из счёта; на нат. 1 — ещё и осечка)</span></label>':''}`)}
  if(P.cm){const have=ST.mat.other.filter(o=>o.q>0&&o.n.toLowerCase().includes(P.cm.k));
    if(P.cm.use){const it=have[0],gold=ST.mat.gold||0,need=P.cm.gp*P.cm.q;
      rows.push(`Компонент: ${esc(P.cm.t)} ×${P.cm.q} — тратится при каждой попытке (8.10): <select class="res-m" aria-label="Компонент"><option value="other" ${it?'selected':''} ${it?'':'disabled'}>из «Прочего»${it?` (${esc(it.n)}: ${it.q})`:' — нет'}</option><option value="gold" ${!it&&gold>=need?'selected':''}>оплатить монетами (−${need} зм)</option><option value="" ${!it&&gold<need?'selected':''}>не списывать</option></select>${!it&&gold<need?' <span class="bad">нет компонента и монет</span>':it&&it.q<P.cm.q?` <span class="bad">есть только ${it.q}</span>`:''}`)}
    else rows.push(`Инструмент рецепта: ${esc(P.cm.t)} — нужен при варке, не тратится (8.10). ${have.length?`Есть: ${esc(have[0].n)}.`:'<span class="bad">В «Прочем» нет</span> — добавь, если есть.'}`)}
  const pl=n=>n%10===1&&n%100!==11?'попытку':[2,3,4].includes(n%10)&&![12,13,14].includes(n%100)?'попытки':'попыток';
  ar.innerHTML=`<div class="sect">Расход на ${P.att} ${pl(P.att)}</div><div class="resb">${rows.map(r=>`<div>${r}</div>`).join('')}</div>`;
  ar.querySelectorAll('select').forEach(x=>{if(keep[x.className]!==undefined&&[...x.options].some(o=>o.value===keep[x.className]))x.value=keep[x.className]});
}
function applyUse(box){ // вызывается внутри mutate
  const P=box._plan;if(!P)return '';const out=[];
  if(P.herbs&&P.herbs.q){const had=herbCount(P.kind,P.herbs.l);
    if(had>=P.herbs.q-1e-9)out.push(`${KIND[P.kind].toLowerCase()} травы ${takeCount(P.kind,P.herbs.q,P.herbs.l)}`);
    else out.push(`травы ур. ${P.herbs.l} не списаны: нужно ${fmtZ(P.herbs.q)}, было ${fmtZ(had)}`)}
  if(P.value&&herbValue(P.kind,P.lvl)<P.value-1e-9)out.push(`травы ур. ${P.lvl}+ не списаны: нужно на ${fmtZ(P.value)} зм, было на ${fmtZ(herbValue(P.kind,P.lvl))}`);
  else if(P.value){out.push(`${KIND[P.kind].toLowerCase()} травы на ${fmtZ(P.value)} зм: ${takeValue(P.kind,P.value,P.lvl)}`)}
  if(P.ess)P.ess.forEach((E,ei)=>{const es=box.querySelector('.res-e'+ei);if(es&&es.value){const e=ST.mat.ess.find(x=>x.id===es.value);if(e){if(e.q<P.att-1e-9)out.push(`эссенция «${e.n}» не списана: нужно ${P.att}, есть ${fmtZ(e.q)}`);else{e.q=+(e.q-P.att).toFixed(2);out.push(`эссенция «${e.n}» −${fmtZ(P.att)}`)}}}});
  const cs=box.querySelector('.res-c');if(P.cat&&cs&&cs.value){const x=ST.mat.cat.find(y=>y.id===cs.value);if(x){x.used=Math.min(cmax(x),x.used+P.att);const cr=box.querySelector('.res-crack');if(cr&&cr.checked){ST.mat.cat=ST.mat.cat.filter(y=>y!==x);out.push(`катализатор ${ROM[x.o]} треснул (5.2)`)}else out.push(`катализатор ${ROM[x.o]} — ${x.used}/${cmax(x)}`)}}
  const ms=box.querySelector('.res-m');if(P.cm&&P.cm.use&&ms&&ms.value){
    if(ms.value==='other'){const it=ST.mat.other.find(o=>o.q>0&&o.n.toLowerCase().includes(P.cm.k));if(it){const t=Math.min(it.q,P.cm.q);it.q-=t;out.push(`«${it.n}» −${t}`)}}
    else if(ms.value==='gold'){const need=P.cm.gp*P.cm.q;if((ST.mat.gold||0)>=need){spendGold(need,P.cm.k);out.push(`${P.cm.k}: −${need} зм монетами`)}else out.push(`${P.cm.k} не оплачена: монет ${fmtZ(ST.mat.gold||0)}`)}}
  ST.mat.herbs=ST.mat.herbs.filter(h=>h.q>0);ST.mat.ess=ST.mat.ess.filter(e=>e.q>0);
  return out.join(', ');
}
function renderMat(){
  const box=$('mat');if(!box)return;box.innerHTML='';
  if(!ST.mat){box.innerHTML='<div class="note">Загрузка…</div>';return}
  const sec=(t)=>{const d=document.createElement('div');d.className='sect';d.textContent=t;box.appendChild(d)};
  const row=(label,sub,q,onm,onp,extra)=>{const r=document.createElement('div');r.className='bagi';
    r.innerHTML=`<span class="nm"></span><button type="button" class="btn sm" aria-label="Меньше">−</button><span class="q">${q}</span><button type="button" class="btn sm" aria-label="Больше">+</button>${extra||''}`;
    r.querySelector('.nm').innerHTML=`${esc(label)}${sub?`<small>${esc(sub)}</small>`:''}`;
    const b=r.querySelectorAll('button');b[0].onclick=onm;b[1].onclick=onp;box.appendChild(r);return r};
  sec('Деньги');
  {const r=document.createElement('div');r.className='bagi';r.innerHTML=`<span class="nm">Монеты Талиса<small>реактивы проб списываются отсюда</small></span><input type="number" step="0.01" value="${ST.mat.gold??0}" aria-label="Монеты, зм" style="width:110px;padding:4px 8px"> <span class="note" style="margin:0">зм</span>`;
   const gi=r.querySelector('input');gi.onchange=()=>mutate(()=>{const v=+gi.value||0;logx(`Монеты: ${fmtZ(ST.mat.gold||0)} → ${fmtZ(v)} зм`);ST.mat.gold=v});box.appendChild(r)}
  sec('Травы');
  const hs=[...ST.mat.herbs].sort((a,b)=>a.k.localeCompare(b.k)||a.l-b.l);
  const pls=pools();
  if(!hs.length&&!pls.length)box.insertAdjacentHTML('beforeend','<div class="note">Нет</div>');
  [...pls].sort((a,b)=>a.k.localeCompare(b.k)||a.min-b.min).forEach(pp=>{const r=document.createElement('div');r.className='bagi';
    r.innerHTML=`<span class="nm">${KIND[pp.k]}, смешанные от ур. ${pp.min}<small>на сумму — для зарядов, склянок, масел кары, чернил до ур. ${pp.min}</small></span><input type="number" step="0.1" min="0" value="${pp.v}" aria-label="Сумма, зм" style="width:96px;padding:4px 8px"> <span class="note" style="margin:0">зм</span>`;
    const inp=r.querySelector('input');inp.onchange=()=>mutate(()=>{pp.v=Math.max(0,+inp.value||0);ST.mat.pools=pools().filter(x=>x.v>0)});box.appendChild(r)});
  hs.forEach(h=>row(`${KIND[h.k]}, ур. ${h.l}`,`${fmtZ(HERB_P[h.l])} зм за траву`,fmtZ(h.q),()=>mutate(()=>{h.q=Math.max(0,+(h.q-1).toFixed(4));ST.mat.herbs=ST.mat.herbs.filter(x=>x.q>1e-9)}),()=>mutate(()=>{h.q++})));
  const fh=document.createElement('div');fh.className='row';fh.style.marginTop='6px';
  fh.innerHTML=`<div><select id="mhk" aria-label="Основа"><option value="heal">Лечебные</option><option value="poison">Ядовитые</option></select></div><div style="flex:.55"><select id="mhl" aria-label="Уровень">${[1,2,3,4,5,6,7,8,9,10].map(l=>`<option value="${l}">ур. ${l}</option>`).join('')}</select></div><div style="flex:.45"><input id="mhq" type="number" min="0" step="0.1" value="1" aria-label="Сколько"></div><div style="flex:.7"><select id="mhu" aria-label="Как"><option value="pc">шт.</option><option value="gp">зм этого ур.</option><option value="mix">зм, смешанные от ур.</option></select></div><div style="flex:none"><button type="button" class="btn" id="mha">+</button></div>`;
  box.appendChild(fh);
  $('mha').onclick=()=>{const k=$('mhk').value,l=+$('mhl').value,v=Math.max(0,+$('mhq').value||0),u=$('mhu').value,gp=u==='gp';if(!v)return;
    mutate(()=>{if(u==='mix'){const pp=pools().find(x=>x.k===k&&x.min===l);if(pp)pp.v=+(pp.v+v).toFixed(2);else pools().push({k,min:l,v});logx(`Материалы: ${KIND[k].toLowerCase()} смешанные травы от ур. ${l} +${fmtZ(v)} зм`);return}
      const q=gp?+(v/HERB_P[l]).toFixed(4):v;const h=ST.mat.herbs.find(x=>x.k===k&&x.l===l);if(h)h.q=+(h.q+q).toFixed(4);else ST.mat.herbs.push({k,l,q});
      logx(`Материалы: ${KIND[k].toLowerCase()} травы ур. ${l} +${fmtZ(q)}${gp?` (на ${fmtZ(v)} зм)`:''}`)})};
  sec('Эссенции');
  if(!ST.mat.ess.length)box.insertAdjacentHTML('beforeend','<div class="note">Нет</div>');
  ST.mat.ess.forEach(e=>row(e.n,`${e.types.join(' / ')} ${ROM[e.l]}${e.note?' · '+e.note:(e.st&&ESS_ST[e.st]?' · '+ESS_ST[e.st]:'')}${essExp(e)?' · '+essExp(e):''}`,fmtZ(e.q),()=>mutate(()=>{e.q--;ST.mat.ess=ST.mat.ess.filter(x=>x.q>0)}),()=>mutate(()=>{e.q++})));
  const fe=document.createElement('div');fe.className='row';fe.style.marginTop='6px';fe.style.flexWrap='wrap';
  fe.innerHTML=`<div style="flex:1 1 130px"><input id="men" type="search" placeholder="Что (чешуя, пыль…)" aria-label="Название"></div><div style="flex:1 1 120px"><input id="met" data-list="essList" type="search" placeholder="Тип" aria-label="Тип эссенции"></div><div style="flex:0 0 74px"><select id="mel" aria-label="Уровень">${[1,2,3,4,5,6,7,8,9,10].map(l=>`<option value="${l}">${ROM[l]}</option>`).join('')}</select></div><div style="flex:none"><button type="button" class="btn" id="mea">+</button></div><label class="tg" style="flex:1 1 100%"><input type="checkbox" id="mef"><span>Влажный трофей, ещё не переработан (9.3)</span></label>`;
  box.appendChild(fe);
  $('mea').onclick=()=>{const t=$('met').value.trim();if(!t)return $('met').focus();const n=$('men').value.trim()||('Эссенция '+t);const l=+$('mel').value;
    mutate(()=>{ST.mat.ess.push({id:uid(),n,types:[t],l,q:1,note:'',st:$('mef').checked?'fresh':'stable'});logx(`Материалы: эссенция «${n}» (${t} ${ROM[l]})`)})};
  sec('Катализаторы');
  if(!ST.mat.cat.length)box.insertAdjacentHTML('beforeend','<div class="note">Нет готовых</div>');
  ST.mat.cat.forEach(x=>{const r=row(`Катализатор ${ROM[x.o]} порядка`,(x.used>=cmax(x)?'исчерпан':x.used>=stab(x)?'дальше — проверки нестабильности (5.2)':`стабильных применений ещё ${stab(x)-x.used}`)+(x.note?' · '+x.note:''),`${x.used}/${cmax(x)}`,
      ()=>mutate(()=>{x.used=Math.max(0,x.used-1)}),()=>mutate(()=>{x.used=Math.min(cmax(x),x.used+1)}),'<button type="button" class="btn sm ghost" aria-label="Убрать">×</button>');
    r.querySelectorAll('button')[2].onclick=()=>mutate(()=>{ST.mat.cat=ST.mat.cat.filter(y=>y!==x);logx(`Материалы: катализатор ${ROM[x.o]} убран`)})});
  const fc=document.createElement('div');fc.className='btns';
  fc.innerHTML=[1,2,3,4].map(o=>`<button type="button" class="btn sm" data-o="${o}">+ катализатор ${ROM[o]}</button>`).join('');
  fc.querySelectorAll('button').forEach(b=>b.onclick=()=>mutate(()=>{ST.mat.cat.push({id:uid(),o:+b.dataset.o,used:0,stable:CAT_STABLE});logx(`Материалы: катализатор ${ROM[+b.dataset.o]} порядка`)}));
  box.appendChild(fc);
  sec('Прочее (вручную)');
  ST.mat.other.filter(o=>o.q>0).forEach(o=>row(o.n,o.note,o.q,()=>mutate(()=>{o.q--}),()=>mutate(()=>{o.q++})));
  const fo=document.createElement('div');fo.className='row';fo.style.marginTop='6px';
  fo.innerHTML=`<div><input id="mon" type="search" placeholder="Сырьё, трофей, компонент…" aria-label="Название"></div><div style="flex:none"><button type="button" class="btn" id="moa">+</button></div>`;box.appendChild(fo);
  $('moa').onclick=()=>{const n=$('mon').value.trim();if(!n)return $('mon').focus();mutate(()=>{const o=ST.mat.other.find(x=>x.n===n);if(o)o.q++;else ST.mat.other.push({n,q:1,note:''});logx(`Материалы: «${n}» +1`)})};
  const rb=document.createElement('button');rb.type='button';rb.className='btn sm ghost';rb.style.marginTop='10px';rb.textContent='Взять материалы заново из листа персонажа';
  rb.onclick=()=>mutate(()=>{ST.mat=JSON.parse(JSON.stringify(SEED.mat));ST.matSeed=SEED.mid;logx('Материалы взяты из листа персонажа')});box.appendChild(rb);
}


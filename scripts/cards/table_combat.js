// ===== Бой: «Мой ход» раз в раунд; лечение зелий по раундам (7.2, Ж-91), яд на оружии (7.5, 8.6). Чужие ходы и цели — у мастера =====
const HEAL_R=__RULE_HEAL_R__, HEAL_F=__RULE_HEAL_F__;
// кубики в порядке потери: сначала меньший, затем основные (7.2)
const HEAL_D=__RULE_HEAL_D__;
const healLvl=n=>{const m=String(n).match(/^Зелье(?: лечения)? (\d+)\.\1\b/);return m&&+m[1]<=10?+m[1]:0};
const healMods=t=>({strong:/\+2 к лечению|Крепк/i.test(t),twin:/Сдвоен/i.test(t),weak:/Слаб/i.test(t),slow:/Медлен/i.test(t)});
function healRound(lv,k,md){const d=HEAL_D[lv].slice(Math.min(k,HEAL_D[lv].length-1)),f=HEAL_F[lv]+(md.strong?2:0),cnt={};
  d.forEach(x=>cnt[x]=(cnt[x]||0)+1);const dice=Object.keys(cnt).map(Number).sort((a,b)=>b-a).map(x=>`${cnt[x]}к${x}`).join('+');
  return dice+(f>0?'+'+f:f<0?'−'+(-f):'')+(md.weak?' −2 (не ниже 1)':'')}
const fight=()=>ST.fight||(ST.fight={on:false,round:0,sub:0,turned:false,heals:[],coats:[],ctl:false,now:[]});
// Ресурсы Талиса живут в том же ST, что сумки: belt/state и резервная копия.
function talis(){
  const defaults={hp:TALIS_LIMITS.hp,temp:0,sp:TALIS_LIMITS.sp,meta:TALIS_LIMITS.meta,
    slots:{...TALIS_LIMITS.slots},concentration:'',reaction:false,dc:null,lastDamage:0};
  if(!ST.talis)ST.talis=defaults;
  else{for(const k of Object.keys(defaults))if(ST.talis[k]===undefined)ST.talis[k]=defaults[k];
    for(const l of Object.keys(TALIS_LIMITS.slots))if(ST.talis.slots[l]===undefined)ST.talis.slots[l]=0}
  return ST.talis;
}
// Ж-145: обе части запаса доступны для любых расходов чародейства.
function sorceryTotal(){const r=talis();return r.sp+r.meta;}
function spendSorcery(n){
  const r=talis();if(!Number.isSafeInteger(n)||n<0||n>sorceryTotal())return false;
  const main=Math.min(r.sp,n);r.sp-=main;r.meta-=n-main;return true;
}
function gainSorcery(n){
  const r=talis();if(!Number.isSafeInteger(n)||n<0||sorceryTotal()+n>TALIS_LIMITS.sp+TALIS_LIMITS.meta)return false;
  const main=Math.min(TALIS_LIMITS.sp-r.sp,n);r.sp+=main;r.meta+=n-main;return true;
}
function damageTalis(n){const r=talis(),used=Math.min(r.temp,n);r.temp-=used;r.hp=Math.max(0,r.hp-(n-used));
  r.lastDamage=n;r.dc=n>0&&r.concentration?Math.max(10,Math.floor(n/2)):null;
  if(r.hp===0)r.concentration='';
  logx(`Талис: урон ${n}, временных потрачено ${used}, хиты ${r.hp}${r.dc?'; СЛ концентрации '+r.dc:''}`);
}
function renderTalis(){const box=$('talis');if(!box)return;const r=talis(),L=TALIS_LIMITS;
  box.innerHTML=`<h3>Талис</h3><p class="note">Максимумы 5-го уровня после отдыха в конце Гильдии: СЛ 15, атака +7, заговоры 2к8. Остатки сохранённого боя не восстанавливаются при обновлении помощника.</p>
    <div class="fresources"><div><b id="fHp">${r.hp} / ${L.hp}</b><div>Хиты</div></div><div><b id="fTemp">${r.temp}</b><div>Временные хиты</div></div></div>
    <div class="btns"><label for="fAmount">Урон после сопротивлений / лечение<input type="number" id="fAmount" min="0" step="1" placeholder="Число, в том числе бросок зелья"></label><button type="button" class="btn soft" id="fDamage">−урон</button><button type="button" class="btn soft" id="fHeal">+лечение</button></div>
    <div class="btns"><label for="fTempAmount">Новые временные хиты<input type="number" id="fTempAmount" min="0" step="1" placeholder="Не складываются"></label><button type="button" class="btn ghost" id="fSetTemp">Оставить большие</button><button type="button" class="btn ghost" id="fClearTemp">Убрать временные</button></div>
    <div class="fresources">${Object.keys(L.slots).map(Number).map(l=>`<div><b id="fSlot${l}">${r.slots[l]} / ${L.slots[l]}</b><div>Ячейки ${ROM[l]} · базовый максимум</div><div class="btns"><button type="button" class="btn sm" data-slot="${l}" ${r.slots[l]>0?'':'disabled'}>Потратить ${ROM[l]}</button><button type="button" class="btn sm ghost" data-to-sp="${l}" ${r.slots[l]>0&&sorceryTotal()+l<=L.sp+L.meta?'':'disabled'}>${ROM[l]} → ${l} ед.</button><button type="button" class="btn sm ghost" data-from-sp="${l}" ${sorceryTotal()>=L.costs[l]?'':'disabled'}>${L.costs[l]} ед. → ${ROM[l]}</button></div></div>`).join('')}</div>
    <p><b id="fSpTotal">${sorceryTotal()} / ${L.sp+L.meta}</b> единиц чародейства в общем пуле.</p><div class="fresources"><div><b id="fSp">${r.sp} / ${L.sp}</b><div>Классовые единицы</div></div><div><b id="fMeta">${r.meta} / ${L.meta}</b><div>От черты, доступны для любых расходов</div></div></div>
    <div class="btns"><label for="fSpAmount">Сколько единиц<input type="number" id="fSpAmount" min="1" step="1" value="1"></label><button type="button" class="btn sm soft" id="fSpendSp">Потратить из общего пула</button><button type="button" class="btn sm soft" id="fSpendMeta">Потратить из запаса черты</button></div>
    <p class="note">Волшебное указание: 1 единица из общего пула за переброс проваленной проверки характеристики; новый результат обязателен. Спасброски и атаки не перебрасывает.</p>
    <p class="note">Преобразование — бонусное действие в свой ход. По разрешению мастера две единицы от черты можно тратить на создание ячеек и Волшебное указание. Общий максимум — 7. Можно списывать из общего пула или сначала использовать запас черты. Созданные ячейки могут превышать базовый запас; при долгом отдыхе исчезают. Здесь отдых не выполняется.</p>
    <label class="f" for="fConcentration">Концентрация на заклинании (отдельно от алхимической)</label><input type="search" id="fConcentration" placeholder="Например, Паутина" value="${esc(r.concentration)}">
    <div class="btns"><button type="button" class="btn sm ghost" id="fStopConcentration">Концентрация прекращена</button><button type="button" class="btn sm soft" id="fReaction" ${r.reaction?'disabled':''}>${r.reaction?'Реакция потрачена до начала моего хода':'Потратить реакцию (Щит)'}</button></div>
    <p class="note" id="fConcentrationDC" aria-live="polite">${r.dc?`Урон ${r.lastDamage}: СЛ концентрации ${r.dc}. Проверь спасбросок; при провале прекрати концентрацию.`:'При уроне: СЛ 10 или половина урона после сопротивлений, что больше; половина округляется вниз.'}${r.hp===0?' Хиты 0: концентрация прекращена. Спасброски от смерти веди отдельно.':''}</p>
    <button type="button" class="btn" id="fWave">После долгого отдыха: восстановить ресурсы</button><p class="note">Нажми после завершённого отдыха. Возвращаются хиты, ячейки и единицы; временные хиты и концентрация снимаются. Расходники сохраняются. Алхимический отдых отмечается отдельно на Поясе.</p>`;
  const amount=id=>{const n=+$(id).value;return $(id).value!==''&&Number.isSafeInteger(n)&&n>=0?n:null};
  $('fDamage').onclick=()=>{const n=amount('fAmount');if(n!==null)mutate(()=>damageTalis(n))};
  $('fHeal').onclick=()=>{const n=amount('fAmount');if(n!==null)mutate(()=>{r.hp=Math.min(L.hp,r.hp+n);logx(`Талис: лечение ${n}, хиты ${r.hp}`)})};
  $('fSetTemp').onclick=()=>{const n=amount('fTempAmount');if(n!==null)mutate(()=>{r.temp=Math.max(r.temp,n);logx(`Талис: временные хиты ${r.temp}`)})};
  $('fClearTemp').onclick=()=>mutate(()=>{r.temp=0;logx('Талис: временные хиты убраны')});
  box.querySelectorAll('[data-slot]').forEach(b=>b.onclick=()=>mutate(()=>{const l=+b.dataset.slot;if(r.slots[l]>0){r.slots[l]--;logx(`Талис: потрачена ячейка ${ROM[l]}`)}}));
  box.querySelectorAll('[data-to-sp]').forEach(b=>b.onclick=()=>mutate(()=>{const l=+b.dataset.toSp;if(r.slots[l]>0&&sorceryTotal()+l<=L.sp+L.meta){r.slots[l]--;gainSorcery(l);logx(`Талис: ячейка ${ROM[l]} → ${l} единиц общего пула (бонусное действие)`)} }));
  box.querySelectorAll('[data-from-sp]').forEach(b=>b.onclick=()=>mutate(()=>{const l=+b.dataset.fromSp;if(sorceryTotal()>=L.costs[l]){spendSorcery(L.costs[l]);r.slots[l]++;logx(`Талис: ${L.costs[l]} единиц общего пула → ячейка ${ROM[l]} (бонусное действие)`)} }));
  $('fSpendSp').onclick=()=>{const n=amount('fSpAmount');if(n!==null&&n>0&&n<=sorceryTotal())mutate(()=>{spendSorcery(n);logx(`Талис: потрачено ${n} единиц из общего пула`)})};
  $('fSpendMeta').onclick=()=>{const n=amount('fSpAmount');if(n!==null&&n>0&&n<=r.meta)mutate(()=>{r.meta-=n;logx(`Талис: потрачено ${n} единиц от черты на разрешённый расход общего пула`)})};
  $('fConcentration').onchange=e=>{const value=e.target.value.trim();mutate(()=>{r.concentration=r.hp>0?value:'';r.dc=null;logx('Талис: концентрация '+(r.concentration||'прекращена'))})};
  $('fStopConcentration').onclick=()=>mutate(()=>{r.concentration='';r.dc=null;logx('Талис: концентрация прекращена')});
  $('fReaction').onclick=()=>mutate(()=>{r.reaction=true;logx('Талис: реакция потрачена')});
  $('fWave').onclick=()=>{if(!confirm('Продолжительный отдых завершён? Восстановить ресурсы 5-го уровня, убрать временные хиты и концентрацию? Расходники останутся.'))return;mutate(()=>{r.hp=L.hp;r.temp=0;r.sp=L.sp;r.meta=L.meta;r.slots={...L.slots};r.concentration='';r.reaction=false;r.dc=null;logx('После долгого отдыха: ресурсы Талиса 5-го уровня восстановлены, временные хиты и концентрация сняты; расходники сохранены')})};
}

// раунды, которые сейчас приходят у последовательности: сдвоенная — первые два сразу
function healTick(h,first){const out=[];const n=first&&h.md.twin?2:1;for(let j=0;j<n&&h.i<HEAL_R[h.lv];j++){out.push(healRound(h.lv,h.i,h.md));h.i++}
  const who=P(h.who)?P(h.who).name:'';return `${who}: «${h.n}» — бросить ${out.join(' и ')} (раунд ${h.i} из ${HEAL_R[h.lv]})`}
function startHeal(who,n,lv,md){const F=fight(),h={id:uid(),who,n,lv,md,i:0};
  if(md.slow){F.now=[`${P(who)?P(who).name:''}: «${n}» медленное — лечение с начала следующего хода`];h.wait=true}else F.now=[healTick(h,true)];
  if(h.i<HEAL_R[lv]||h.wait)F.heals.push(h);logx(`Бой: ${P(who)?P(who).name+' — ':''}«${n}», лечение по раундам`)}
function myTurn(pid){const F=fight(),out=[];
  if(pid==='p1'){talis().reaction=false;if(F.turned){F.round++;F.sub++;if(F.sub>=10){F.sub=0;ST.T+=1}}F.turned=true;F.ctl=false}
  F.heals.filter(h=>h.who===pid).forEach(h=>{if(h.wait){h.wait=false;out.push(healTick(h,true))}else out.push(healTick(h,false))});
  F.heals=F.heals.filter(h=>h.wait||h.i<HEAL_R[h.lv]);
  if(pid==='p1'){ST.ent.filter(e=>e.who==='p1'&&isActive(e)).forEach(e=>{const r=Math.max(0,Math.round((endOf(e)-ST.T)*10-F.sub));if(r<=1)out.push(`«${e.n}» кончается${r?' в этом раунде':''} — проверь`)});
    const tx=toxOfP('p1'),t=P('p1');if(tx)out.push(`Токсичность ${fmtZ(tx)} из ${t.limit}${tx>t.limit?' — выше предела':''}`);
    F.coats.filter(c=>c.who==='p1').forEach(c=>out.push(`На оружии «${c.n}»: ${c.ctl?'контрольный, до попадания':'атак осталось '+c.left}`))}
  F.now=out.length?out:['Ничего не срабатывает'];logx(`Бой: ${pid==='p1'?'раунд '+F.round+', ход Талиса':'ход '+(P(pid)?P(pid).name:'')}`)}
// вид пояса: auto — «Только бой», пока идёт бой; ручной выбор держится до начала или конца боя
let BV=['auto','all','combat'].includes(ls.get('beltView'))?ls.get('beltView'):'auto', lastOn=null;
function applyBV(on){const c=BV==='combat'||(BV==='auto'&&on),t=$('tab-belt'),b=$('beltView');if(t)t.classList.toggle('combat',c);if(b)b.setAttribute('aria-pressed',c);document.body.classList.toggle('battle-mobile',!!(c&&t&&!t.hidden))}
$('mobileTools').onclick=()=>{const open=document.body.classList.toggle('battle-header-open');$('mobileTools').setAttribute('aria-expanded',open)};
$('beltView').onclick=()=>{BV=$('beltView').getAttribute('aria-pressed')==='true'?'all':'combat';ls.set('beltView',BV);applyBV(fight().on)};
{const lim=()=>{$('pl').value=Math.max(0,(+$('pcon').value||0)+(+$('ppb').value||0)+2)};$('pcon').oninput=lim;$('ppb').oninput=lim}
function renderFight(){const box=$('fight');if(!box)return;const F=fight();
  if(lastOn!==null&&lastOn!==!!F.on){BV='auto';ls.set('beltView',BV)}lastOn=!!F.on;applyBV(F.on);
  if(!F.on){box.innerHTML=`<div class="row" style="align-items:center"><h2 style="margin:0;flex:1">Бой</h2><button type="button" class="btn" id="fStart">Начать бой</button></div><p class="note">В бою: «Мой ход» в начале каждого хода Талиса — сдвигает время на раунд (10 раундов = 1 минута) и показывает, что сейчас бросить и проверить. Зелье лечения, потраченное из сумки, само идёт по раундам (7.2). Чужие ходы, спасброски врагов и сроки контроля на целях ведёт мастер.</p>`;
    $('fStart').onclick=()=>mutate(()=>{Object.assign(F,{on:true,round:1,sub:0,turned:false,heals:[],ctl:false,now:['Бой начат. Нажми «Мой ход» в начале хода Талиса.']});logx('Бой начат')});return}
  const others=ST.people.filter(p=>p.id!=='p1'&&F.heals.some(h=>h.who===p.id));
  const bagPs=ST.bag.filter(b=>b.q>0&&(/^Яд \d+\.\d+/.test(b.n)||(bagCard(b)&&bagCard(b).k==='psn')));
  box.innerHTML=`<div class="row" style="align-items:center;flex-wrap:wrap"><h2 style="margin:0;flex:1">Бой · раунд ${F.round}</h2>
    <button type="button" class="btn" id="fTurn" style="background:var(--acc);color:var(--panel);border-color:var(--acc);font-weight:600">Мой ход</button>
    ${others.map(p=>`<button type="button" class="btn soft" data-ot="${p.id}">Ход: ${esc(p.name)}</button>`).join('')}
    <button type="button" class="btn ghost" id="fEnd">Конец боя</button></div>
    <section class="talis" id="talis" aria-label="Ресурсы Талиса"></section>
    <div class="fnow">${F.now.map(t=>`<div>${esc(t)}</div>`).join('')}</div>
    <div class="fgrid"><div><div class="sect">Лечение по раундам</div><div id="fHeals"></div>
      <div class="row" style="flex-wrap:wrap;margin-top:6px"><div style="flex:0 0 90px"><select id="fhL" aria-label="Уровень зелья">${[1,2,3,4,5,6,7,8,9,10].map(l=>`<option value="${l}">${l}.${l}</option>`).join('')}</select></div>
        <div style="flex:1 1 100px"><select id="fhW" aria-label="Кто выпил">${ST.people.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('')}</select></div>
        <div style="flex:1 1 130px"><select id="fhM" aria-label="Бонус или дефект"><option value="">обычное</option><option value="+2 к лечению">крепкое (+2)</option><option value="Сдвоенная">сдвоенное</option><option value="Слабое">слабое (−2)</option><option value="Медленное">медленное</option></select></div>
        <div style="flex:0 0 auto"><button type="button" class="btn sm" id="fhAdd">Выпито не из сумки</button></div></div></div>
    <div><div class="sect">Яд на оружии</div><div id="fCoats"></div>
      <div class="row" style="flex-wrap:wrap;margin-top:6px"><div style="flex:1 1 160px"><select id="fcB" aria-label="Яд из сумки">${bagPs.map((b,i)=>`<option value="${i}">${esc(b.n)} — ${esc(P(b.who)?P(b.who).name:'')} (${b.q})</option>`).join('')||'<option value="">в сумках нет ядов</option>'}</select></div>
        <div style="flex:0 0 auto"><button type="button" class="btn sm" id="fcAdd"${bagPs.length?'':' disabled'}>Нанести</button></div></div>
      <p class="note">Обычный яд — 5 атак, попал или нет (7.5). Контрольный — до первого попадания; от одного отравителя одна попытка за раунд, лишнее попадание дозу не тратит, а если яд на цели уже действует — тратится (8.6, Ж-99).</p></div></div>`;
  renderTalis();
  const HB=$('fHeals');if(!F.heals.length)HB.innerHTML='<div class="note">Нет</div>';
  F.heals.forEach(h=>{const r=document.createElement('div');r.className='bagi';r.innerHTML=`<span class="nm"></span>`;
    r.querySelector('.nm').innerHTML=`${esc(h.n)}<small>${esc(P(h.who)?P(h.who).name:'')} · ${h.wait?'начнётся со следующего хода':`дальше ${healRound(h.lv,h.i,h.md)} · осталось раундов ${HEAL_R[h.lv]-h.i}`}</small>`;HB.appendChild(r)});
  const CB=$('fCoats');const mine=F.coats;if(!mine.length)CB.innerHTML='<div class="note">Нет</div>';
  mine.forEach(c=>{const r=document.createElement('div');r.className='bagi';
    r.innerHTML=`<span class="nm"></span><button type="button" class="btn sm" data-h="1">Попал</button><button type="button" class="btn sm soft" data-h="0">Мимо</button><button type="button" class="btn sm ghost" aria-label="Снять">×</button>`;
    r.querySelector('.nm').innerHTML=`${esc(c.n)}<small>${esc(P(c.who)?P(c.who).name:'')} · ${c.ctl?(c.who==='p1'&&F.ctl?'попытка в этом раунде уже была':'контрольный, до первого попадания'):'атак осталось '+c.left}</small>`;
    const b=r.querySelectorAll('button');
    b[0].onclick=()=>mutate(()=>{if(!c.ctl){c.left--;F.now=[`«${c.n}»: попадание — яд действует (урон и спасбросок — у мастера). Атак осталось ${c.left}`]}
      else if(c.who==='p1'&&F.ctl){F.now=[`«${c.n}»: попытка в этом раунде уже была — лишнее попадание дозу не тратит. Если яд на цели уже действует — доза тратится: сними её ×`]}
      else{c.left=0;if(c.who==='p1')F.ctl=true;F.now=[`«${c.n}»: попадание — цель делает спасбросок (если он есть); доза потрачена`]}
      logx(`Бой: «${c.n}» — попадание`);F.coats=F.coats.filter(x=>x.left>0)});
    b[1].onclick=()=>mutate(()=>{if(!c.ctl)c.left--;F.now=[`«${c.n}»: промах${c.ctl?' — доза остаётся':` — атака потрачена, осталось ${c.left}`}`];F.coats=F.coats.filter(x=>x.left>0)});
    b[2].onclick=()=>mutate(()=>{F.coats=F.coats.filter(x=>x!==c)});CB.appendChild(r)});
  $('fTurn').onclick=()=>mutate(()=>myTurn('p1'));
  box.querySelectorAll('[data-ot]').forEach(b=>b.onclick=()=>mutate(()=>myTurn(b.dataset.ot)));
  $('fEnd').onclick=()=>mutate(()=>{const rest=F.heals.map(h=>{const o=[];while(h.i<HEAL_R[h.lv]){o.push(healRound(h.lv,h.i,h.md));h.i++}return o.length?`${P(h.who)?P(h.who).name:''}: «${h.n}» — ${o.join(', ')}`:''}).filter(Boolean);
    if(F.sub>0)ST.T+=1;F.on=false;F.heals=[];logx('Бой окончен'+(rest.length?'. Лечение доходит в следующие раунды: '+rest.join('; '):''));
    F.now=[];F.coats=F.coats.filter(c=>!c.ctl||c.left>0)});
  $('fhAdd').onclick=()=>mutate(()=>{const lv=+$('fhL').value;startHeal($('fhW').value,`Зелье лечения ${lv}.${lv}`+($('fhM').value?` (${$('fhM').value})`:''),lv,healMods($('fhM').value))});
  $('fcAdd').onclick=()=>{const b=bagPs[+$('fcB').value];if(!b)return;mutate(()=>{const c=bagCard(b),ctl=!!(c&&c.k==='psn'),t=(b.note||'')+' '+b.n;
    b.q--;F.coats.push({id:uid(),who:b.who,n:b.n,ctl,left:ctl?1:/долг/i.test(t)?6:/Коротк/i.test(t)?3:5});logx(`Бой: ${P(b.who)?P(b.who).name:''} наносит «${b.n}»`);F.now=[`«${b.n}» нанесён (действие; с чертой «Отравитель» — бонусное)`]})};
}


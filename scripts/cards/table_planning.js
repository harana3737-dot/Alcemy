// Сценарии планирования хранятся отдельно от фактических ресурсов и журнала.
const PLAN_RULES=__PLANNING_RULES__;
let BP={budget:null,hours:2,need:'Лечение',stockOnly:false,search:'',week:12,progress:null};
try{const saved=JSON.parse(ls.get('brewing-plan')||'null');if(saved&&typeof saved==='object')for(const key of Object.keys(BP))if(Object.hasOwn(saved,key))BP[key]=saved[key]}catch(e){}
const PLAN_NEEDS=['Лечение','Защита','Контроль','Мобильность','Разведка','Урон','Рост мастерства'];
function recipeNeeds(c){
  if(c.k==='basic')return c.b==='лечебная'?['Лечение']:['Урон'];
  const tags=c.tk||[],text=(Array.isArray(tags)?tags.join(' '):String(tags)).toLowerCase();
  const map={'Лечение':/лечен|восстанов|хиты|исцелен/,'Защита':/защит|сопротив|кд|спасброс|временн/,'Контроль':/контрол|обездвиж|оглуш|опут|очаров|ослеп|страх/,'Мобильность':/мобиль|движ|скорост|полёт|телепорт/,'Разведка':/развед|восприят|скрыт|зрен|общен|обнаруж/,'Урон':/урон/};
  return Object.entries(map).filter(([,re])=>re.test(text)).map(([n])=>n);
}
function planChance(c,bonus,unstable=S.t.ess){
  const dc=(c.k==='basic'?PLAN_RULES.potionDC[c.l]:DC[c.l-1])+(unstable&&c.k!=='basic'?2:0);
  const p=chancesTxt(dc,bonus+(S.t.help?2:0));
  return {dc,p,success:p.ok+p.hi+p.n20,growth:p.ok+p.hi+2*p.n20};
}
// Точное ожидание числа полных партий до цели: прибавки 0/1/2 за дозу.
// Включает избыток прогресса в последней партии, но не создаёт реальные успехи.
function expectedBatches(remaining,size,success,natural20=.05){
  if(remaining<=0)return 0;
  let pmf=[1];
  for(let i=0;i<size;i++){const next=Array(pmf.length+2).fill(0);pmf.forEach((p,j)=>{next[j]+=p*(1-success);next[j+1]+=p*(success-natural20);next[j+2]+=p*natural20});pmf=next}
  if(pmf[0]>=1-1e-12)return Infinity;
  const expected=Array(remaining+1).fill(0);
  for(let r=1;r<=remaining;r++){let value=1;for(let gain=1;gain<pmf.length;gain++)value+=pmf[gain]*expected[Math.max(0,r-gain)];expected[r]=value/(1-pmf[0])}
  return expected[remaining];
}
// Ожидание подходов по 6.3: учитывает половину прогресса, нат. 1 и границу нуля.
// Метки/дефекты меняют завершающую проверку, а не объём; простой здесь отсутствует.
const VOLUME_CACHE=new Map();
function volumeHours(level,dc,bonus){
  const volume=VOLUME(level),key=[volume,dc,bonus].join(':');if(VOLUME_CACHE.has(key))return VOLUME_CACHE.get(key);
  const transitions=[];
  for(let r=2;r<=20;r++){const total=r+bonus;transitions.push([r===20?2*total:total>=dc?total:total>=dc-4?Math.floor(total/2):0,.05])}
  for(let n=1;n<=20;n++)transitions.push([-n,.0025]);
  const E=Array(volume+1).fill(0);
  for(let sweep=0;sweep<1000;sweep++){
    let change=0;
    for(let i=volume-1;i>=0;i--){let value=1,self=0;for(const [delta,p] of transitions){const j=Math.max(0,Math.min(volume,i+delta));if(j===i)self+=p;else value+=p*E[j]}value/=1-self;change=Math.max(change,Math.abs(value-E[i]));E[i]=value}
    if(change<1e-8)break;
  }
  const result=E[0]*2;VOLUME_CACHE.set(key,result);return result;
}
function masteryForecast(M,B,progress,week){
  if(M>=10)return null;
  const target=PLAN_RULES.growth[M],remaining=Math.max(0,target-progress),c={k:'basic',l:M};
  const chance=planChance(c,B),batch=batchInfo('',M,null,M,S.t.lab),batches=expectedBatches(remaining,batch.size,chance.success),attempts=batches*batch.size;
  // Консервативно: полная стоимость трав, без выбора экономии за качество.
  // Катализатор — 5 стабильных применений; ремонт и риск сверх ресурса исключены.
  const perDose=M*HERB_P[M]+PLAN_RULES.catalyst[M]/5;
  return {target,remaining,dc:chance.dc,bonus:B+(S.t.help?2:0),success:chance.success,size:batch.size,batches,attempts,hours:batches*batch.t,gold:attempts*perDose,herbs:attempts*M,catalystUses:M>=3?attempts:0,weeks:week>0?batches*batch.t/week:null};
}
function recommendBrews(config){
  const M=Math.max(1,Math.min(10,+$('m').value||1)),B=+$('b').value||0,budget=Math.max(0,+config.budget||0),hours=Math.max(0,+config.hours||0),result=[];
  for(const c of RECIPES){
    if(!knows(c)||c.l>M||c.l>(S.t.lab?10:$('anar').checked?8:5))continue;
    if(config.search&&!c.n.toLowerCase().includes(String(config.search).toLowerCase()))continue;
    const needs=recipeNeeds(c),growth=c.l===M;
    if(config.need==='Рост мастерства'?!growth:config.need&&!needs.includes(config.need))continue;
    const check=supply(c),unknown=check.deficits.some(d=>d.price==null),cost=check.deficits.reduce((s,d)=>s+(d.price||0),0);
    if(unknown||cost>budget+1e-8||config.stockOnly&&check.deficits.length)continue;
    const chance=planChance(c,B,S.t.ess||check.warnings.some(w=>w.startsWith('нестабильная эссенция'))),batch=batchInfo(c.n,c.l,c.k==='basic'?null:c,M,S.t.lab);
    const long=c.k!=='basic'&&c.l>=6;
    const time=long?volumeHours(c.l,chance.dc,B+(S.t.help?2:0)):batch.t;
    if(time>hours+1e-8)continue;
        // Рекомендация — отдельная альтернатива, не общий комплект с общими материалами.
    result.push({c,check,cost,time,long,chance,needs,growth});
  }
  // Рекомендации Codex: сначала без докупки, затем цена; при равной цене —
  // шанс годной дозы, время и название. Не выдумываем численную «силу» эффекта.
  return result.sort((a,b)=>a.cost-b.cost||b.chance.success-a.chance.success||a.time-b.time||a.c.n.localeCompare(b.c.n,'ru'));
}
function saveBrewingPlan(){ls.set('brewing-plan',JSON.stringify(BP));renderBrewingPlan()}
function renderBrewingPlan(){
  const box=$('brewingPlanning');if(!box||$('tab-brewing-plan').hidden)return;
  const M=Math.max(1,Math.min(10,+$('m').value||1)),B=+$('b').value||0;
  const track=TR.find(t=>t.group==='mastery'&&(t.id===`mastery-${M}-${M+1}`||t.name===`Мастерство ${M} → ${M+1}`));
  const progress=BP.progress==null?Math.max(0,+track?.current||0):Math.max(0,Math.floor(+BP.progress||0)),week=Math.max(0,+BP.week||0),forecast=masteryForecast(M,B,progress,week);
  const budget=BP.budget==null?ST.mat.gold||0:Math.max(0,+BP.budget||0),options=recommendBrews({...BP,budget});
  box.innerHTML=`<div class="card"><h2>До следующего мастерства</h2><p>Мастерство ${M} · общий бонус варки ${B>=0?'+':''}${B}${S.t.help?' +2 от помощника':''}. Бонус и мастерство берутся с вкладки «Варка».</p><div class="row"><div><label class="f">Уже набрано успехов <small>Пусто — брать из журнала</small></label><input id="bpProgress" type="number" min="0" max="25" value="${BP.progress==null?'':progress}" placeholder="${progress}"></div><div><label class="f">Часов варки в неделю</label><input id="bpWeek" type="number" min="0" max="168" value="${week}"></div></div><div id="bpForecast">${M<10&&!knows(BASIC.find(c=>c.l===M&&c.b==='лечебная'))?'<p class="note">Рецепт зелья лечения этого уровня не отмечен известным: прогноз — сценарий после освоения рецепта (либо для известного яда того же уровня).</p>':''}${!forecast?'<p>Мастерство X: следующей ступени нет.</p>':`<p>До ${M+1}: <b>${forecast.remaining} из ${forecast.target}</b> успехов. Зелья уровня ${M}, СЛ ${forecast.dc}, годная доза ${pct(forecast.success)}, партия ${forecast.size}.</p><p>В среднем: <b>${fmtZ(forecast.hours)} ч</b> · ${fmtZ(forecast.batches)} партий · ${fmtZ(forecast.attempts)} попыток${forecast.weeks==null?'':' · '+fmtZ(forecast.weeks)+' недель'}.</p><p>Стоимость расхода: <b>${fmtZ(forecast.gold)} зм</b>; травы ур. ${M}: ${fmtZ(forecast.herbs)} шт${forecast.catalystUses?' · применений катализатора: '+fmtZ(forecast.catalystUses):''}.</p>`}</div><p class="note">Ожидание, не срок с гарантией: каждую дозу проверяют отдельно, натуральная 20 даёт два успеха. Модель — освоенные зелья текущего уровня, обычные партии, неизменный бонус, без ремонтных осечек, нестабильных катализаторов, руководства и перерывов. Полная ценность расхода включает уже имеющиеся материалы; это не список докупки. Экономия трав за 5+ не заложена. Будущий уровень персонажа автоматически не повышается.</p></div>
  <div class="card" style="margin-top:16px"><h2>Что варить сегодня</h2><p class="note">Рекомендации Codex. Пять отдельных альтернатив на одну дозу / попытку, каждая проверяется по текущему запасу. Порядок: минимум докупки, затем шанс годной дозы и время. Известные рецепты отметь в «Что могу сварить».</p><div class="row"><div><label class="f">Бюджет докупки, зм <small>Пусто — деньги из материалов</small></label><input id="bpBudget" type="number" min="0" value="${BP.budget==null?'':budget}" placeholder="${budget}"></div><div><label class="f">Есть часов</label><input id="bpHours" type="number" min="0" max="10000" step="0.5" value="${Math.max(0,+BP.hours||0)}"></div><div><label class="f">Нужда группы</label><select id="bpNeed"><option value="">Любая</option>${PLAN_NEEDS.map(n=>`<option>${n}</option>`).join('')}</select></div></div><div class="row"><div><label class="f">Поиск рецепта</label><input id="bpSearch" type="search" value="${esc(String(BP.search||''))}"></div><label class="tg"><input id="bpStock" type="checkbox" ${BP.stockOnly?'checked':''}><span>Только имеющиеся материалы</span></label></div><div id="bpOptions">${!options.length?'<p>Подходящих варок нет: проверь известные рецепты, мастерство, оборудование, время, бюджет и материалы. Позиции с неизвестной ценой не считаются доступными за деньги.</p>':`<p>Подходит: ${options.length}. Показаны первые пять.</p>`+options.slice(0,5).map((r,i)=>`<div class="card"><h3>${esc(r.c.n)} · ${ROM[r.c.l]}</h3><p>Докупка ${fmtZ(r.cost)} зм · ${r.long?'ожидаемая работа ≈':'время '}${fmtZ(r.time)} ч · ${r.long?'шанс завершающей проверки до меток и дефектов':'годная доза'} ${pct(r.chance.success)}${r.growth?' · ожидаемый рост '+fmtZ(r.chance.growth)+' на проверку':''}.</p>${r.long?'<p class="note">VI+: время без простоев, с заминками и потерей прогресса. Метки и дефекты меняют финальный шанс; часы — среднее, фактическая варка может не уложиться.</p>':''}${r.check.deficits.length?'<ul>'+r.check.deficits.map(d=>`<li>${esc(d.n)}: ${fmtZ(d.q)} · ${fmtZ(d.price)} зм</li>`).join('')+'</ul>':'<p>Материалы на попытку есть.</p>'}${r.check.warnings.length?'<p class="note">'+r.check.warnings.map(esc).join(' · ')+'</p>':''}<button type="button" class="btn soft bpOpen" data-index="${i}">Открыть рецепт</button></div>`).join('')}</div><p class="note">Докупка — справочные цены; наличие у продавца проверяет мастер. Нестабильная эссенция добавляет +2 к СЛ в прогнозе; риск катализатора не включён в шанс. Подбор не расходует материалы, деньги и часы и не обещает готовую дозу. Категории берутся из задач карточек; эффекты сверяй по рецепту.</p></div>`;
  $('bpNeed').value=BP.need;
  for(const [id,key] of [['bpProgress','progress'],['bpBudget','budget'],['bpWeek','week'],['bpHours','hours']])$(id).onchange=e=>{BP[key]=e.target.value===''&&['progress','budget'].includes(key)?null:Math.max(0,Math.min(key==='progress'?25:key==='week'?168:1000000,+e.target.value||0));saveBrewingPlan()};
  $('bpNeed').onchange=e=>{BP.need=e.target.value;saveBrewingPlan()};$('bpStock').onchange=e=>{BP.stockOnly=e.target.checked;saveBrewingPlan()};
  $('bpSearch').onchange=e=>{BP.search=e.target.value;saveBrewingPlan()};
  box.querySelectorAll('.bpOpen').forEach(el=>el.onclick=()=>{tab('brew');chooseAvailableRecipe(options[+el.dataset.index].c);$('out').scrollIntoView({block:'start'})});
}

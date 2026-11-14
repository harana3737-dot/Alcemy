"""Точные опорные расчёты стратегии; не изменяет игровые сохранения.

--write / --check: JSON совместной цепочки I–III, роста и тактических изделий.
Условная оценка времени не является обещанием простоя или дохода.
"""
import argparse
from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path
import re
import sys

from alchemy_guidance import chances
from current_inventory import load
from economy_book import formula_research, progress_research
from rules_data import (BATCH_T, CAT_PRICE, CAT_STABLE, ELIXIR_DC, HERB,
                        INK_PRICES, MB, P_PRICE, P_SL,
                        proficiency, elixir_batch)

sys.path.insert(0, str(Path(__file__).resolve().parent / 'cards'))
from cards_data import C

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'scripts/development_strategy'


def rolls(bonus, dc, points):
    """Один переброс любого провала; нестабильность тоже провал проверки."""
    for first in range(1, 21):
        failed = first == 1 or first != 20 and first + bonus < dc
        if failed and points:
            for final in range(1, 21):
                yield final, points - 1, 1 / 400
        else:
            yield first, points, 1 / 20


def ink(bonus, level=2, guidance=True, sale=.85):
    dc = ELIXIR_DC[level]
    dist = defaultdict(float)
    for face, _, mass in rolls(bonus, dc, int(guidance)):
        status = ('stable' if face == 20 or face != 1 and face + bonus >= dc else
                  'unstable' if face != 1 and face + bonus >= dc - 4 else 'lost')
        dist[status] += mass
    price = INK_PRICES[level]
    cost = price / 3 + HERB[level]
    revenue = price * (sale * dist['stable'] + .5 * dist['unstable'])
    return dict(bonus=bonus, level=level, guidance=guidance, sale=sale,
                cost=cost, **dist, profit=revenue-cost,
                profit_per_hour=(revenue-cost)/(2 if level <= 2 else 4))


def growth(remaining, mastery, bonus, guidance=True):
    """Точное ожидание полных партий лечения I–V до перехода.

    Нат.20: +2 практики независимо от бонуса; выбираются экономия + качество,
    не дополнительная доза. Катализатор считается по стабильным применениям;
    целый катализатор для запуска показан отдельно. Нет цены исследования.
    """
    if not 1 <= mastery <= 5:
        raise ValueError('Для VI+ нужен расчёт объёма, не короткая партия')
    batch = BATCH_T[mastery][mastery-1]
    outcomes = defaultdict(float)
    save = 0.
    for face, _, mass in rolls(bonus, P_SL[mastery], int(guidance)):
        gain = 2 if face == 20 else int(face != 1 and face+bonus >= P_SL[mastery])
        outcomes[gain] += mass
        if face == 20 or face != 1 and face+bonus >= P_SL[mastery]+5:
            save += mass
    distribution = {0: 1.}
    for _ in range(batch):
        nxt = defaultdict(float)
        for a, pa in distribution.items():
            for b, pb in outcomes.items():
                nxt[a+b] += pa*pb
        distribution = dict(nxt)
    @lru_cache(None)
    def batches(left):
        if left <= 0:
            return 0.
        return (1+sum(p*batches(max(0,left-g)) for g,p in distribution.items() if g))/(1-distribution.get(0,0))
    n = batches(remaining)
    herbs = mastery*HERB[mastery]*(1-save)
    cost = n*batch*(herbs+CAT_PRICE[mastery]/CAT_STABLE)
    return dict(remaining=remaining, mastery=mastery, bonus=bonus, guidance=guidance, batch=batch,
                expected_batches=n, hours=2*n, attempts=batch*n,
                allocated_cost=cost, initial_cat=CAT_PRICE[mastery])


def research(bonus):
    # Образец 2.2 даёт 1 из 3 отметок и +2; запас перебросов 3 без новых отдыхов.
    trials, points = formula_research(2, P_SL[2], bonus+2, 3)
    return dict(bonus=bonus, attempts=trials, hours=2*trials,
                herbs=trials*2*HERB[2]/4, points=points,
                sample_opportunity=P_PRICE[2])


SCROLL_PRICES = {1: 60, 2: 250, 3: 600}
SLOTS_LAEL = {1: 4, 2: 3, 3: 2}


@lru_cache(None)
def ink_rolls(level, bonus, points):
    result=defaultdict(float)
    for face,left,p in rolls(bonus,ELIXIR_DC[level],points):
        if face==1 or face!=20 and face+bonus<ELIXIR_DC[level]-4:
            quality=None
        elif face!=20 and face+bonus<ELIXIR_DC[level]:
            quality=-2
        else:
            quality=4 if face==20 else 2 if face+bonus>=ELIXIR_DC[level]+5 else 0
        result[quality,left]+=p
    return tuple((quality,left,p) for (quality,left),p in result.items())


@lru_cache(None)
def scroll_rolls(level, quality, nth, luck):
    """Везунчик 2014: лучший из двух, только на неудаче, максимум один пункт."""
    bonus=10+quality-2*(nth-1);dc=10+2*level
    result=defaultdict(float)
    for first in range(1,21):
        retry=bool(luck and (first==1 or first!=20 and first+bonus<dc))
        for second in (range(1,21) if retry else (first,)):
            face=max(first,second) if retry else first
            status=('lost' if face==1 or face!=20 and face+bonus<dc-4 else
                    'stable' if face==20 or face+bonus>=dc else 'unstable')
            result[status,luck-int(retry)]+=1/(400 if retry else 20)
    return tuple((status,left,p) for (status,left),p in result.items())


def chain(level, bonus, *, lucky=True, sale=.75, ink_sale=.75, accept_unstable=True):
    """На один исходный подход; первое Начертание после реального отдыха.

    Учитываем все чернила, в том числе нестабильные. Не продаём дефектные
    свитки, не кредитуем экономию материалов и не оцениваем ячейки монетами.
    """
    material=INK_PRICES[level]/3+HERB[level]
    allocated=material+CAT_PRICE[level]/CAT_STABLE
    accepted=success=unstable=luck_use=direct=direct_premium=0.
    for quality,_,p in ink_rolls(level,bonus,1):
        if quality is None:
            continue
        direct+=p*INK_PRICES[level]*(.5 if quality<0 else ink_sale)
        direct_premium+=p*INK_PRICES[level]*(.5 if quality<0 else ink_sale*(2 if quality==4 else 1.5 if quality==2 else 1))
        if quality<0 and not accept_unstable:
            continue
        accepted+=p
        for status,left,q in scroll_rolls(level,quality,1,int(lucky)):
            success+=p*q*(status=='stable');unstable+=p*q*(status=='unstable')
            luck_use+=p*q*(int(lucky)-left)
    price=SCROLL_PRICES[level];duration=2 if level<=2 else 4
    return dict(level=level,bonus=bonus,lucky=lucky,accept_unstable=accept_unstable,scroll_sale_fraction=sale,
                first_attempt_cash=material+CAT_PRICE[level],allocated_per_attempt=allocated,
                ink_accepted=accepted,stable_per_attempt=success,unstable_per_attempt=unstable,
                cost_per_stable=allocated/success,talis_hours_per_stable=duration/success,
                lael_hours_per_stable=2*accepted/success,slots_per_stable=accepted/success,
                luck_per_stable=luck_use/success,scroll_sale_price=price*sale,
                profit_per_production_attempt=price*sale*success-allocated,
                net_per_stable=price*sale-allocated/success,
                direct_ink_profit=direct-allocated,
                scroll_increment_per_lael_hour=(price*sale*success-direct)/(2*accepted),
                break_even_scroll_sale_fraction=direct/(price*success),
                break_even_with_quality_premium=direct_premium/(price*success))


def joint_cycle(level=2, bonus=5, attempts=2, *, luck=3, guide=3, slots=None, sale=.75, consult=False):
    """Конечный блок без отдыхов: очередь, слоты, усталость, время отдельно.

    Талис работает последовательно, Лаэль начинает сразу после получения
    очередного набора и освобождения от предыдущей работы. Не помещающиеся
    в слоты чернила остаются запасом, не считаются свитками или выручкой.
    """
    slots=SLOTS_LAEL[level] if slots is None else slots
    if attempts<1 or slots<0 or luck<0 or guide<0:
        raise ValueError("Неверный размер блока или запас ресурсов")
    duration=2 if level<=2 else 4
    # Остатки ресурсов, число Начертаний/стабильных/дефектных/ожидающих, конец письма.
    states={(guide,luck,0,0,0,0,0,0):1.}
    for attempt in range(1,attempts+1):
        nxt=defaultdict(float)
        for (g,l,used,good,bad,waiting,end,t_end),probability in states.items():
            production_end=t_end+duration
            if consult:
                production_end=max(production_end-.5,end)+.5
            writer_end=production_end if consult else end
            for quality,left,p in ink_rolls(level,bonus+int(consult),g):
                if quality is None or used>=slots:
                    key=(left,l,used,good,bad,waiting+int(quality is not None),writer_end,production_end)
                    nxt[key]+=probability*p
                    continue
                finish=max(production_end,writer_end)+2
                for status,new_l,q in scroll_rolls(level,quality,used+1,l):
                    key=(left,new_l,used+1,good+int(status=='stable'),bad+int(status=='unstable'),waiting,finish,production_end)
                    nxt[key]+=probability*p*q
        states=nxt
    assert abs(sum(states.values())-1)<1e-9
    material=INK_PRICES[level]/3+HERB[level]
    cash=attempts*material+(CAT_PRICE[level]*((attempts+CAT_STABLE-1)//CAT_STABLE))
    mean=lambda f:sum(f(k)*p for k,p in states.items())
    good=mean(lambda k:k[3]);sold=mean(lambda k:max(0,k[3]-1))
    ideal_t=ideal_l=0
    for i in range(attempts):
        ideal_t+=duration
        if consult:
            ideal_t=max(ideal_t-.5,ideal_l)+.5
            ideal_l=ideal_t
        if i<slots:
            ideal_l=max(ideal_t,ideal_l)+2
    return dict(level=level,bonus=bonus,attempts=attempts,initial_guide=guide,initial_luck=luck,
        slot_limit=slots,consult=consult,consultation_hours=.5*attempts if consult else 0,cash_upfront=cash,talis_hours=duration*attempts,
        lael_hours=2*mean(lambda k:k[2])+(.5*attempts if consult else 0),slots_used=mean(lambda k:k[2]),
        guide_used=guide-mean(lambda k:k[0]),luck_used=luck-mean(lambda k:k[1]),
        elapsed_work_only=mean(lambda k:max(k[7],k[6])),
        ideal_elapsed_with_available_slots=max(ideal_t,ideal_l),
        stable_scrolls=good,unstable_scrolls=mean(lambda k:k[4]),waiting_inks=mean(lambda k:k[5]),
        probability_two_stable=sum(p for k,p in states.items() if k[3]>=2),
        stable_distribution={str(i):sum(p for k,p in states.items() if k[3]==i) for i in range(attempts+1)},
        all_sold_cash_net=good*SCROLL_PRICES[level]*sale-cash,
        first_kept_scrolls=mean(lambda k:min(1,k[3])),excess_sold_scrolls=sold,
        first_kept_cash_net=sold*SCROLL_PRICES[level]*sale-cash)


def mixed_two_cycles():
    block=joint_cycle()
    distribution={int(k):v for k,v in block['stable_distribution'].items()}
    totals=defaultdict(float)
    for a,pa in distribution.items():
        for b,pb in distribution.items():
            totals[a+b]+=pa*pb
    stock=sum(min(2,n)*p for n,p in totals.items())
    sold=sum(max(0,n-2)*p for n,p in totals.items())
    return dict(attempts=4,cash_without_interim_sales=162,talis_hours=8,
                lael_hours=2*block['lael_hours'],separate_resource_cycles=2,
                group_stock=stock,sold=sold,conditional_cash_net=sold*187.5-162,
                probability_stock_two=sum(p for n,p in totals.items() if n>=2))


def tactical(name):
    c=next(c for c in C if c['name']==name);l=c['lvl']
    price=float(re.search(r'[\d.]+',c['price'].replace(' ','')).group())
    base=price/3 if c['cls'] in ('chg','rea','fl','psn','oils') else l*HERB[l]
    # Все выбранные цели требуют одну эссенцию своего уровня и не имеют дорогого компонента.
    material=base+HERB[l];duration=2 if l<=2 else 4
    bonus=proficiency(5)+MB[5]+3
    first=chances(bonus,ELIXIR_DC[l]+2,True)[0]
    known=chances(bonus,ELIXIR_DC[l],True)[0]
    expected_cash=material/first+(CAT_PRICE[l]/(1-(1-first)**CAT_STABLE) if CAT_PRICE[l] else 0)
    return dict(name=name,level=l,kind=c['cls'],essence=c['ess'],price=price,
                base=base,raw_material=material,catalyst=CAT_PRICE[l],
                first_attempt_cash=material+CAT_PRICE[l],duration=duration,
                stable_first=first,stable_known=known,first_stable_hours=duration/first,
                first_stable_cash=expected_cash,
                allocated_known_per_stable=(material+CAT_PRICE[l]/CAT_STABLE)/known,
                toxicity=c['tox'],concentration=c.get('concentration',False),effect=c['eff'])


def validate_sources():
    """Не переносить старые цены и правило закупки в новую редакцию молча."""
    page=(ROOT/'Шпаргалка свитков.html').read_text()
    for label,expected in (('Материалы, зм',[15,30,120,300]),
                           ('Готовый свиток, зм',[30,60,250,600])):
        row=re.search(r'<tr><td>'+re.escape(label)+r'</td>(.*?)</tr>',page,re.S)
        if not row:
            raise ValueError('Нет исходной строки цен: '+label)
        values=re.findall(r'<td[^>]*>(.*?)</td>',row[1],re.S)
        actual=[int(re.sub(r'<[^>]+>|\s','',v)) for v in values[:4]]
        if actual!=expected:
            raise ValueError('Изменились цены свитков/чернил: пересмотреть стратегию')
    rules=(ROOT/'Алхимия Талиса — полные правила v0.3.md').read_text()
    if 'На деле Гильдия берёт за 75%' not in rules or 'свитки Лаэля' not in rules:
        raise ValueError('Перепроверить подтверждение закупки собственных свитков')
    if 'помогает не меньше 30 минут' not in rules:
        raise ValueError('Перепроверить условия консультации Лаэля')


def mixed_program(hours, policy='healing_first', ready=False):
    """Конечный бюджет M2: исследования, освоение и смеси; без перебросов.

    После нат.1 работа приостанавливается до решения мастера, после M3 —
    до нового плана. Так неизвестная осечка не становится бесплатной.
    """
    if hours not in (8, 12, 20) or policy not in ('healing_first', 'body_first'):
        raise ValueError('Неизвестная программа')
    names = ('ink', 'healing', 'aid', 'shield', 'practice', 'cash', 'hours',
             'body_essence_I', 'body_essence_II', 'ink_essence_II',
             'sample_used', 'heal_recipe', 'body_recipe', 'aid_mastered',
             'full_aid_sets', 'shield_casts', 'paused', 'mastery3', 'unpaired_ink')
    # State: ink attempts, heal/body marks, shield/aid mastery, ordinary
    # healing doses, aid doses, shield doses, practice in half-points, mix index,
    # consumed sample, completed healing opening and an unpaired ordinary ink.
    initial = (0, 3 if ready else 1, 3 if ready else 0,
               int(ready), int(ready), 0, 0, 0, 8, 0, 0, int(ready), 0)

    def action(state):
        ink_n, hm, bm, sm, am, heals, aids, shields, practice2, mix, sample, heal_open, unpaired = state
        if ink_n < 2:
            return 'ink'
        if not ready:
            if policy == 'healing_first':
                if hm < 3:
                    return 'research_heal'
                if heals < 2:
                    return 'healing'
            if bm < 3:
                return 'research_body'
            if not sm:
                return 'shield'
            if not am or policy == 'body_first' and aids < 3:
                return 'aid'
            if hm < 3:
                return 'research_heal'
        return ('healing', 'aid', 'shield', 'healing', 'aid', 'healing', 'aid', 'shield')[mix % 8]

    @lru_cache(None)
    def solve(remaining, state, paused=False):
        ink_n, hm, bm, sm, am, heals, aids, shields, practice2, mix, sample, heal_open, unpaired = state
        if not remaining or paused or practice2 >= 30:
            terminal = dict(heal_recipe=heal_open, body_recipe=int(bm >= 3 and sm),
                            aid_mastered=am, full_aid_sets=aids//3,
                            shield_casts=shields, paused=int(paused),
                            mastery3=int(practice2 >= 30), unpaired_ink=unpaired)
            return tuple(float(terminal.get(k, 0)) for k in names)
        kind = action(state)
        count = 2 if kind == 'healing' or kind == 'aid' and am else 3 if kind == 'shield' and sm else 1
        if kind.startswith('research'):
            count = 1
        # Outcomes include stable doses and practice; stop a batch on nat.1.
        outcomes = {(0, 0, False): 1.}
        dc = 10 if kind in ('healing', 'research_heal') else 12
        if kind == 'aid' and not am or kind == 'shield' and not sm:
            dc += 2
        bonus = 9 if kind.startswith('research') else 7
        for _ in range(count):
            nxt = defaultdict(float)
            for (stable, gain2, pause), prob in outcomes.items():
                if pause:
                    nxt[(stable, gain2, pause)] += prob
                    continue
                for face in range(1, 21):
                    success = face != 1 and (face == 20 or face+bonus >= dc)
                    gain = (3 if face == 20 else 2 if face+bonus >= dc+5 else int(success)) if kind.startswith('research') else 0
                    dose = int(success and not kind.startswith('research'))
                    if kind == 'ink':
                        practice_gain = 2 if face == 20 else int(success)
                    elif kind in ('healing', 'aid'):
                        practice_gain = 4 if face == 20 else 2*int(success)
                    else:
                        practice_gain = 0
                    nxt[(stable+dose, gain2+gain+practice_gain, face == 1)] += prob/20
            outcomes = nxt
        result = [0.]*len(names)
        for (stable, gain, pause), prob in outcomes.items():
            values = list(state); reward = defaultdict(float)
            reward['hours'] = 2
            if kind == 'research_heal':
                values[1] = min(3, hm+gain)
                reward['cash'] = .25
                reward['sample_used'] = int(not sample)
                values[10] = 1
            elif kind == 'research_body':
                values[2] = min(3, bm+gain)
                reward['cash'] = 5.125
                reward['body_essence_I'] = 1
            else:
                reward[kind] = stable
                if kind == 'ink' and stable and gain == 1:
                    values[12] = 1-unpaired
                    gain = 2*unpaired
                values[8] += gain; reward['practice'] = gain/2
                if kind == 'ink':
                    values[0] += 1; reward['cash'] = 40.5
                    reward['ink_essence_II'] = 1
                elif kind == 'healing':
                    values[5] += stable; reward['cash'] = count*1.
                    if stable and not heal_open:
                        values[11] = 1; values[8] += 2; reward['practice'] += 1
                elif kind == 'aid':
                    values[6] += stable; values[4] = int(am or stable)
                    reward['cash'] = count*1.5; reward['body_essence_II'] = count
                else:
                    values[7] += stable; values[3] = int(sm or stable)
                    if stable and not sm:
                        values[8] += 2; reward['practice'] += 1
                    reward['cash'] = count*.2; reward['body_essence_I'] = count
                # Only the repeatable mixed-production tail advances the index.
                if kind != 'ink' and (ready or hm >= 3 and bm >= 3 and sm and am and (policy != 'body_first' or aids >= 3) and (policy != 'healing_first' or heals >= 2)):
                    values[9] += 1
            future = solve(remaining-1, tuple(values), pause)
            for j, key in enumerate(names):
                result[j] += prob*(reward[key]+future[j])
        return tuple(result)

    result = dict(zip(names, solve(hours//2, initial)))
    return dict(budget_hours=hours, policy=policy, recipes_ready=ready,
                expected=result, assumptions=dict(bonus=7, guidance=0,
                    research_hint=2, initial_practice=4, ink_attempts=2,
                    stop_on_natural1=True, stop_on_mastery3=True,
                    batch_materials_reserved_in_full=True,
                    repair_travel_training_hours_excluded=True))


def build():
    validate_sources()
    result=dict(goal='M5 и устойчивое снабжение группы; коммерция — дополнительный источник',
        confirmed_cash=load()['state']['mat']['gold'],
        assumptions=dict(lael_base_bonus=10,scroll_market=SCROLL_PRICES,
            scroll_sale_fraction=.75,crafted_scroll_sale_confirmed=True,
            sale_source="Полные правила, справочник цен: со слов игрока, собственные свитки Лаэля тоже 75%",
            guaranteed_buy_volume=None,refund_credit=0,unstable_scroll_revenue=0,
            ink_quality_premium_in_baseline=False,
            talis_weekly_alchemy_hours=[20,22],lael_hours='отдельный бюджет',
            travel_trade_repair_in_alchemy_cap='не установлено; считать отдельно',
            inventory_sharing='не согласовано; прибыль цепочки не личный кошелёк Талиса'),
        chain=[chain(l,b,lucky=lucky) for l in (1,2,3) for b in (5,7) for lucky in (False,True)],
        stable_inks_only=[chain(l,b,accept_unstable=False) for l in (1,2,3) for b in (5,7)],
        cycles=[joint_cycle(l,b,n,luck=luck) for l,n in ((1,3),(2,2),(2,3),(3,2),(3,3))
                for b in (5,7) for luck in (0,3)],
        growth=[growth(r,m,b) for m,r in ((2,9),(3,20),(4,25)) for b in (proficiency(5)+MB[m]+1,proficiency(5)+MB[m]+3)],
        healing2_research=[research(b) for b in (5,7)],
        recipe_100=[dict(bonus=b,attempts=progress_research(100,b,3)[0],
                         gold=progress_research(100,b,3)[1],hours=2*progress_research(100,b,3)[0]) for b in (5,7,8)],
        mixed_two_cycles=mixed_two_cycles(),
        mixed_programs=[mixed_program(h,p,ready) for ready in (False,True)
                        for p in (('healing_first',) if ready else ('healing_first','body_first')) for h in (8,12,20)],
        consulted_cycles=[joint_cycle(l,b,2,consult=True) for l,b in ((2,5),(3,7))],
        finance_bridge_M4=[dict(sale=s,first_cash=472,two_attempt_cash=874,
            profit_per_attempt=ink(8,4,True,s)['profit']-CAT_PRICE[4]/CAT_STABLE)
            for s in (.75,.85)],
        mastery5_batches=dict(healing=list(BATCH_T[5]),elixir=[elixir_batch(5,l,False) for l in range(1,6)],charge=1,flask=1),
        targets=[tactical(n) for n in ('Склянка стихии: большая','Молниевый выдох','Склянка стихии: малая',
            'Контрзаклинание','Сковывающая склянка: замедление','Благословение',
            'Щит веры','Шаг сквозь туман','Зеркальные образы','Защита от смерти')])
    return json.dumps(result,ensure_ascii=False,indent=2)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true');parser.add_argument('--check',action='store_true')
    args=parser.parse_args();content=build();path=OUTPUT/'results.json'
    if args.check:
        if not path.exists() or path.read_text()!=content:
            raise SystemExit('Устарел расчёт совместной стратегии: results.json')
        print('PASS: цепочка I–III, конечные ресурсы, параллельность, M5 и выбранные средства воспроизводятся')
    elif args.write:
        OUTPUT.mkdir(exist_ok=True);path.write_text(content)
    else:
        print(content)


if __name__=='__main__':
    main()

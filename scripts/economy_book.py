"""Таблицы книги экономики: общие правила, точные исследования, явные сценарии."""
import argparse
from math import fsum
from pathlib import Path
import random
import re

from rules_data import (MB, HERB, P_SL, NEED, ELIXIR_DC, CAT_PRICE,
                        CAT_STABLE, proficiency, unstable_fraction)
from sim import INK, probs, scenario, p_bonus
from sim_plan import batch_p, week
from sim_volume import volume_stats, CHG, ESS

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / 'Для игрока — книга экономики.md'


def number(value, digits=2):
    return f'{value:,.{digits}f}'.replace(',', ' ').replace('.', ',')


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join('---' for _ in headers) + ' |',
                      *['| ' + ' | '.join(map(str, row)) + ' |' for row in rows]])


def bonus(level, mastery, lab):
    return proficiency(level) + MB[mastery] + lab


def progress_research(remaining, check_bonus, points=0):
    """100 прогресса: один переброс только натуральной 1, итог определяет расход."""
    trials = [[0.] * (remaining + 1) for _ in range(points + 1)]
    costs = [[0.] * (remaining + 1) for _ in range(points + 1)]
    spent = [[0.] * (remaining + 1) for _ in range(points + 1)]
    price = lambda die: 60 if die == 1 else 0 if die == 20 else 30
    for pool in range(points + 1):
        for rem in range(1, remaining + 1):
            for die in range(1, 21):
                outcomes = [(die, pool, 1 / 20, 0)]
                if die == 1 and pool:
                    outcomes = [(new, pool - 1, 1 / 400, 1) for new in range(1, 21)]
                for final, next_pool, probability, use in outcomes:
                    next_rem = max(0, rem - final - check_bonus)
                    trials[pool][rem] += probability * (1 + trials[next_pool][next_rem])
                    costs[pool][rem] += probability * (price(final) + costs[next_pool][next_rem])
                    spent[pool][rem] += probability * (use + spent[next_pool][next_rem])
    return trials[points][remaining], costs[points][remaining], spent[points][remaining]


def formula_research(target, dc, check_bonus, points=0):
    """Отметки: переброс любого провала; доп. последствия осечек не назначаются."""
    trials = [[0.] * (target + 1) for _ in range(points + 1)]
    spent = [[0.] * (target + 1) for _ in range(points + 1)]
    def marks(die):
        if die == 1:
            return 0
        if die == 20:
            return 3
        if die + check_bonus >= dc + 5:
            return 2
        return int(die + check_bonus >= dc)
    for pool in range(points + 1):
        for rem in range(1, target + 1):
            n, use, same = 1., 0., 0.
            for die in range(1, 21):
                gain = marks(die)
                if not gain and pool:
                    use += 1 / 20
                    for new in range(1, 21):
                        next_rem = max(0, rem - marks(new))
                        n += trials[pool - 1][next_rem] / 400
                        use += spent[pool - 1][next_rem] / 400
                elif not gain:
                    same += 1 / 20
                else:
                    next_rem = max(0, rem - gain)
                    n += trials[pool][next_rem] / 20
                    use += spent[pool][next_rem] / 20
            trials[pool][rem], spent[pool][rem] = n / (1 - same), use / (1 - same)
    return trials[points][target], spent[points][target]


def growth_attempts(target, check_bonus, dc):
    ok, _, _ = probs(check_bonus, dc)
    expectations = [0.] * (target + 1)
    for rem in range(1, target + 1):
        expectations[rem] = (1 + (ok - .05) * expectations[rem - 1]
                             + .05 * expectations[max(0, rem - 2)]) / ok
    return expectations[target]


def sections():
    examples = [(3, 1, 1), (5, 2, 1), (6, 3, 1), (9, 5, 1),
                (11, 7, 3), (13, 8, 3), (17, 9, 5), (20, 10, 5)]
    out = {}
    out['bonuses'] = table(['Чародей', 'Алхимия', 'Инструменты', 'Мастерство', 'Место', 'Общий бонус'],
                          [(cl, m, f'+{proficiency(cl)}', f'+{MB[m]}', f'+{lab}', f'+{bonus(cl,m,lab)}')
                           for cl,m,lab in examples])
    brewing = [(3,1,1,1), (5,2,1,1), (5,2,1,2), (6,3,1,3), (9,5,1,5),
               (11,7,3,6), (13,8,3,8), (17,9,5,9), (20,10,5,10)]
    out['brewing'] = table(['Чародей / алхимия', 'Лечение', 'Бонус / СЛ', 'Доз в партии', 'Успех', 'Стабильных доз в среднем'],
        [(f'{cl} / {m}', f'{l}.{l}', f'+{bonus(cl,m,lab)} / {P_SL[l]}', batch_p(m,l),
          number(probs(bonus(cl,m,lab), P_SL[l])[0]*100,0)+'%',
          number(batch_p(m,l)*probs(bonus(cl,m,lab),P_SL[l])[0],1)) for cl,m,lab,l in brewing])
    rows=[]
    for rem,b in [(70,5),(70,7),(100,5)]:
        for pts in (0,5):
            n,c,s=progress_research(rem,b,pts)
            rows.append([rem,f'+{b}', 'единицы' if pts else 'нет',number(n*2),number(c),number(s)])
    out['progress'] = table(['Осталось прогресса', 'Бонус', 'Переброс', 'Часы', 'Травы, зм', 'Единиц в среднем'],rows)
    rows=[]
    for cl,m,lab,l,marks,h in [(5,2,1,2,3,2),(6,3,1,3,4,2),(9,5,1,5,4,2),
                              (11,7,3,6,5,2),(11,7,3,7,5,2),
                              (13,8,3,8,6,6),(17,9,5,9,6,6)]:
        b=bonus(cl,m,lab)+2
        n0,_=formula_research(marks,ELIXIR_DC[l],b)
        n,s=formula_research(marks,ELIXIR_DC[l],b,cl)
        rows.append([f'{cl} / {m}',l,f'+{b} / {ELIXIR_DC[l]}',number(n0*h),number(n*h),number((n0-n)*h),number(s)])
    out['formulas'] = table(['Чародей / алхимия', 'Цель', 'Проверка / СЛ', 'Без указания, ч', 'С указанием, ч', 'Экономия, ч', 'Единиц в среднем'],rows)
    rows=[]
    for cl,m,lab,l in [(5,2,1,2),(6,3,1,3),(9,5,1,5)]:
        b=bonus(cl,m,lab);pr,herb,ess,dc,cat,h=INK[['','I','II','III','IV','V'][l]]
        results=[scenario(b,dc,herb+ess,pr*sale,CAT_PRICE[cat],unstable_fraction(sale),h,item_kind='ink',level=l)
                 for sale in (.85,.75)]
        rows.append([f'{cl} / {m}',l,f'+{b}',number(herb+ess),number(CAT_PRICE[cat]),number(results[0]['per_day']/8),number(results[1]['per_day']/8)])
    out['ink-sales'] = table(['Чародей / алхимия', 'Чернила', 'Бонус', 'Материалы попытки, зм', 'Целый катализатор, зм', 'Прибыль/ч: 85%', 'Прибыль/ч: 75%'],rows)
    rows=[]
    for cl,m,lab in examples:
        if m>=10:
            continue
        b=bonus(cl,m,lab);n=growth_attempts(NEED[m],b,P_SL[m]);high,crit=p_bonus(b,P_SL[m])
        cost=n*(m*HERB[m]*(1-high-crit)+CAT_PRICE[m]/CAT_STABLE)
        rows.append([f'{cl} / {m}',f'{m} → {m+1}',NEED[m],number(n*2/batch_p(m,m),1),number(cost,0)])
    out['growth'] = table(['Чародей / алхимия', 'Переход', 'Практики', 'Часы, примерно', 'Материалы и доля катализатора, зм'],rows)
    rows=[]
    for cl,m,lab,l in [(11,7,3,6),(13,8,3,8)]:
        b=bonus(cl,m,lab);price=CHG[l];mat=price/3+ESS[l]
        r=volume_stats(b,l,price,mat,runs=20000,rng=random.Random(20261012+l))
        rows.append([f'{cl} / {m}',l,f'+{b}',number(mat+CAT_PRICE[l]/CAT_STABLE,0),number(r['hours'],1),number(r['ok']*100,0)+'%',number(r['profit']/r['hours'],0)])
    out['long'] = table(['Чародей / алхимия', 'Заряд или чернила', 'Бонус', 'Расход одной варки, зм', 'Часы, примерно', 'Стабильный результат', 'Прибыль/ч при 85%, зм'],rows)
    rows=[]
    price,herb,ess,dc,cat,h=INK['II']
    hourly=scenario(5,dc,herb+ess,price*.85,CAT_PRICE[cat],unstable_fraction(.85),h,
                    item_kind='ink',level=2)['per_day']/8
    income={'pot':0,'ink':(hourly,'II'),'vol':None}
    for h in (12,22,30):
        w=week(2,2,2,2,h,income=income)
        cost=fsum(w[k][1] for k in ('ink','kit','heal'))
        rows.append([h,number(w['fixed'],1),number(cost,1),
                     'не хватает '+number(w['shortfall_hours'],1)+' ч' if not w['fits_expected_budget'] else number(w['free'],1)+' ч',
                     '—' if not w['fits_expected_budget'] else number(w['sale'],1),
                     '—' if not w['fits_expected_budget'] else number(w['sale']-cost,1)])
    out['weeks'] = table(['Бюджет, ч', 'Снабжение, ч', 'Материалы снабжения, зм', 'Остаток времени', 'Прибыль продаж, зм', 'Изменение кошелька, зм'],rows)
    return out


def build():
    text=BOOK.read_text(encoding='utf-8')
    for key,value in sections().items():
        pattern=rf'(<!-- economy:{re.escape(key)}:start -->).*?(<!-- economy:{re.escape(key)}:end -->)'
        text,n=re.subn(pattern,lambda m:m[1]+'\n'+value+'\n'+m[2],text,flags=re.S)
        if n!=1:
            raise ValueError('Не найден единственный блок таблицы: '+key)
    return text


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true');parser.add_argument('--check',action='store_true')
    args=parser.parse_args();result=build()
    if args.check:
        if BOOK.read_text(encoding='utf-8')!=result:
            raise SystemExit('Таблицы книги экономики устарели; пересоберите --write.')
        print('PASS: восемь таблиц экономики воспроизводятся из общих правил')
    elif args.write:
        BOOK.write_text(result,encoding='utf-8');print('Собраны восемь таблиц книги экономики')
    else:
        print(result)

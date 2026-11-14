"""Точные опорные расчёты стратегии; не изменяет игровые сохранения.

--write / --check: JSON расчётов и полный отбор каталога CSV.
Условная оценка времени не является обещанием простоя или дохода.
"""
import argparse
from collections import defaultdict
import csv
from functools import lru_cache
import io
import json
from pathlib import Path
import re
import sys

from alchemy_guidance import chances
from current_inventory import load
from economy_book import formula_research, progress_research
from rules_data import (BATCH_T, CAT_PRICE, CAT_STABLE, ELIXIR_DC, HERB,
                        INK_PRICES, MB, P_PRICE, P_SL,
                        normal_brewing_allowed, proficiency)
from scenario_engine import Scenario, finite_exact

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


def fund(initial, target, *, attempts=2, points=3, reserve=20, sale=.85):
    """Конечный кошелёк: продаём по одному, останавливаемся при цели/дефиците.

    Цены в медных монетах; без продажи будущих подарков, кредита и новых отдыхов.
    Не оплачивает ремонт: только вероятность сначала собрать нужные деньги.
    """
    active = {(round(initial*100), points, 0): 1.}
    terminal = defaultdict(float)
    goal, floor, cost = round(target*100), round(reserve*100), 4050
    for step in range(attempts+1):
        following = defaultdict(float)
        for (cash, pool, used), probability in active.items():
            if cash >= goal or step == attempts or cash-cost < floor:
                terminal[cash, used] += probability
                continue
            for face, left, mass in rolls(5, 12, pool):
                revenue = round(120*sale*100) if face == 20 or face != 1 and face+5 >= 12 else 6000 if face != 1 and face+5 >= 8 else 0
                following[cash-cost+revenue, left, used+1] += probability*mass
        active = following
    return dict(initial=initial, target=target, reserve=reserve, max_attempts=attempts,
                points=points, sale=sale,
                funded=sum(p for (cash, _), p in terminal.items() if cash >= goal),
                expected_attempts=sum(n*p for (_, n), p in terminal.items()),
                expected_cash=sum(cash*p/100 for (cash, _), p in terminal.items()),
                minimum_cash=min(cash/100 for cash, _ in terminal),
                lose_cash=sum(p for (cash, _), p in terminal.items() if cash < round(initial*100)))


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


def formula(c):
    if c['cls'] in ('oilw','oils','salve'):
        return 'Масла и мази'
    essence = re.split(r'\s+(?:X|IX|VIII|VII|VI|V|IV|III|II|I)\b', c['ess'])[0]
    if essence.startswith('Стихия'):
        essence = 'Стихия'
    if c['cls'] in ('chg','rea','fl'):
        return 'Заряды и склянки: '+essence
    if c['cls'] == 'psn':
        return 'Контрольные яды: '+essence
    return 'Эликсир '+('Сноровки' if c['name'].startswith('Сноровка') else essence)


def screening():
    selected = {'Благословение':'Первый кандидат против атак и спасбросков; Разум',
                'Бдительный отдых':'Кандидат на возврат времени, нужен сюжетный повод; Разум',
                'Шаг сквозь туман':'Первый кандидат на аварийный выход; Движение',
                'Щит веры':'Запасной выбор под атаки, особенно Фаэнону; Тело',
                'Защита от смерти':'Цель M4 при реальной угрозе смерти; Смерть/душа',
                'Зеркальные образы':'Цель M3 против видящих атакующих; Покров',
                'Психическая стойкость':'Цель M3 против контроля; Разум'}
    rows=[]
    for c in C:
        price=float(re.search(r'[\d.]+',c['price'].replace(' ','')).group())
        l=c['lvl']; by_value=c['cls'] in ('fl','chg','psn','rea','oils')
        herbs=price/3 if by_value else l*HERB[l]
        why=selected.get(c['name'], 'Сравнивать с конкретной угрозой; отдельный ранний приоритет не назначен')
        if c['cls'] in ('chg','rea','fl'):
            why='Отложить самостоятельное исследование: 100 прогресса на тип; взять найденный рецепт или готовое средство под угрозу'
        elif c['cls'] == 'psn':
            why='Отложить: иммунитеты нежити/сопротивления и цена открытия; проверить конкретного противника'
        elif c['cls'] in ('oilw','oils','salve'):
            why='Отложить покупку рецепта за 500 зм; магический меч Фаэнона ограничивает часть масел'
        rows.append(dict(name=c['name'],level=l,kind=c['cls'],formula=formula(c),
                         ordinary_at_M2_place1=normal_brewing_allowed(l,2,1),
                         confirmed_recipe=False,price=price,base_per_attempt=herbs,
                         essence=c['ess'],catalyst_upfront=CAT_PRICE[l],
                         raw_effect=c['eff'],reason=why))
    return rows


def healing_stock(quantity, bonus=5):
    from math import comb
    p=chances(bonus,P_SL[2],True)[0]
    @lru_cache(None)
    def batches(left):
        if left<=0:
            return 0.
        return (1+sum(comb(2,k)*p**k*(1-p)**(2-k)*batches(max(0,left-k))
                      for k in (1,2)))/(1-(1-p)**2)
    n=batches(quantity); saved=0.
    for face,_,mass in rolls(bonus,P_SL[2],1):
        if face==20 or face!=1 and face+bonus>=P_SL[2]+5:
            saved+=mass
    return dict(quantity=quantity,bonus=bonus,hours=2*n,
                materials=2*n*(1-saved),buy=quantity*P_PRICE[2])


def entry(name, bonus=5, sample=True):
    c=next(c for c in C if c['name']==name)
    target=2 if sample else 3
    dc=ELIXIR_DC[c['lvl']] + (0 if sample else 2)
    trials, points=formula_research(target,dc,bonus+(2 if sample else 0),3)
    base=c['lvl']*HERB[c['lvl']]
    reagents=5 + base/4 + HERB[c['lvl']]
    specimen=float(c['price']) if sample else 0
    return dict(name=name,bonus=bonus,sample=sample,hours=2*trials,
                cost=trials*reagents+specimen,points=points,
                first_variant_stable=chances(bonus,ELIXIR_DC[c['lvl']]+2,True)[0])


def build():
    cash=load()['state']['mat']['gold']
    a,b=ink(5),ink(7)
    improvement=(b['profit']-a['profit'])/2
    data=dict(snapshot_cash=cash, assumptions=dict(sale=.85,alternative_sale=.75,
        reserve_proposed=20,weekly_total=22,buffer_proposed=4,stable_cat_uses=5,
        osseka_extra_cost='не установлена; не назначена нулевой фактической тратой'),
        ink=[ink(b,l,g,s) for l in (1,2) for b in (5,7) for g in (False,True) for s in (.75,.85)],
        laboratory=dict(cash_cost=50,repair_hours=6,profit_improvement_per_hour=improvement,
            cash_only_payback_hours=50/improvement,
            including_six_hours_opportunity=(50+6*a['profit_per_hour'])/improvement,
            expected_two_stable_cost_before=2*a['cost']/a['stable'],
            expected_two_stable_cost_after=2*b['cost']/b['stable']),
        funding=[fund(cash,151,sale=s,points=p) for s in (.75,.85) for p in (0,3)],
        healing2_research=[research(b) for b in (5,7)],
        growth=[growth(r,m,b,g) for m,r in ((2,11),(2,9),(3,20),(4,25),(5,25))
                for b in ((5,7) if m<=3 else (6,8)) for g in (False,True)],
        healing_stock=[healing_stock(q,b) for q in (2,6,9) for b in (5,7)],
        hundred_progress=[dict(bonus=b,attempts=progress_research(100,b,3)[0],
            cost=progress_research(100,b,3)[1],hours=2*progress_research(100,b,3)[0]) for b in (5,7)],
        formula_entry=[entry(n,b,s) for n in ('Благословение','Щит веры','Шаг сквозь туман') for b in (5,7) for s in (False,True)],
        ink_long=[])
    for level in (5,9,13,17,20):
        for m in (3,4,5):
            bonus=proficiency(level)+MB[m]+3
            mat=INK_PRICES[m]/3+HERB[m]
            # 30 отдельных производственных дней; не прогноз календаря.
            s=Scenario(bonus,ELIXIR_DC[m],mat,.85*INK_PRICES[m],CAT_PRICE[m],m,
                       item_kind='ink',points=2,per_day=2,days=30,stop=5)
            result=finite_exact(s)
            data['ink_long'].append(dict(class_level=level,mastery=m,bonus=bonus,
                 initial_outlay=mat+CAT_PRICE[m],profit_per_hour=result['per_day']/8))
    from party_kit_report import CARDS, small
    data['supply_comparison']=[]
    for name,q in (('Благословение',3),('Щит веры',3),('Шаг сквозь туман',2),('Бдительный отдых',1)):
        for lab in (1,3):
            cost,hours,p=small(CARDS[name],2,q,level=5,lab=lab,guidance=True)
            data['supply_comparison'].append(dict(name=name,quantity=q,place=lab,
                known_recipe=True,materials=cost,hours=hours,stable=p,
                shadow_cost_at_ink2_city=cost+hours*a['profit_per_hour']))
    csvout=io.StringIO();rows=screening()
    writer=csv.DictWriter(csvout,fieldnames=list(rows[0]),lineterminator="\n");writer.writeheader();writer.writerows(rows)
    return json.dumps(data,ensure_ascii=False,indent=2)+'\n',csvout.getvalue()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true');parser.add_argument('--check',action='store_true')
    args=parser.parse_args();data,screen=build()
    for name,content in (('results.json',data),('catalog_screen.csv',screen)):
        path=OUTPUT/name
        if args.check:
            if not path.exists() or path.read_text()!=content:
                raise SystemExit('Устарел расчёт стратегии: '+name)
        elif args.write:
            OUTPUT.mkdir(exist_ok=True);path.write_text(content)
        else:
            print(content if name=='results.json' else f'Каталог: {len(C)} карточек')
    if args.check:
        print(f'PASS: стратегия, конечный кошелёк и отбор {len(C)} карточек воспроизводятся')


if __name__=='__main__':
    main()

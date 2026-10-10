"""Исследование дневной ёмкости рынка и выбора перебросов; не новые правила.

Ёмкость — продаваемые дозы за день. Непроданное хранится без денежной оценки,
перепродажа в последующие дни не моделируется. Очки/ёмкость сбрасываются в начале дня.
"""
import argparse
from dataclasses import dataclass
import json
import math
import random
import statistics
from rules_data import CAT_STABLE, INSTAB, P_PRICE
from scenario_engine import potion
from sim import check_success, probs
from sim_guidance import outcome


@dataclass
class Solution:
    scenario: object
    capacity: object
    policy: str
    profit: float
    brew_retry: list
    risk_retry: list
    quality: list


def payouts(s, d, quota):
    """Варианты выручки и остатка лимита; экономия трав не занимает спрос."""
    def sale(count,price):
        sold=count if quota==-1 else min(count,quota)
        return sold*price, -1 if quota==-1 else quota-sold
    r=outcome(d,s.bonus,s.sl)
    if r=='fail':return [(0.,quota)]
    if r=='unst':return [sale(1,s.price*s.unst_value)]
    basic=sale(1,s.price)
    if s.item_kind!='potion':return [basic]
    if d==20:
        up=s.price/P_PRICE[s.level]*P_PRICE[s.level+1] if s.level<(10 if s.allow_up_to_10 else 9) else s.price
        return [(basic[0]+s.mat,basic[1]),sale(2,s.price),sale(1,up)]
    if d+s.bonus>=s.sl+5:return [(basic[0]+s.mat,basic[1])]
    return [basic]


def solve(s, *, capacity=None, policy='optimal'):
    if policy not in ('historical','optimal'):raise ValueError('Неизвестная политика')
    if capacity is not None and (type(capacity) is not int or capacity<0):raise ValueError('Ёмкость должна быть неотрицательным целым или None')
    quotas=(-1,) if capacity is None else range(capacity+1)
    horizon=s.days*s.per_day
    if horizon*s.stop*(s.points+1)*len(quotas)>500000:raise ValueError('Слишком большая сетка состояний; сократи горизонт или запасы')
    initial_quota=-1 if capacity is None else capacity
    next_values={};brew_policy=[None]*horizon;risk_policy=[None]*horizon;quality_policy=[None]*horizon
    ok,un,_=probs(s.bonus,s.sl)
    historical_unst=ok+un*s.unst_value>s.unst_value
    for step in reversed(range(horizon)):
        def future(used,points,quota):
            if step+1==horizon:return 0.
            if (step+1)%s.per_day==0:points=s.points;quota=initial_quota
            return next_values[used,points,quota]
        values={};brews={};br={};rr={};qp={}
        for used in range(s.stop):
            use=used+1
            next_use=0 if use>=s.stop or not s.cat and use>=CAT_STABLE else use
            for quota in quotas:
                for points in range(s.points+1):
                    state=(used,points,quota)
                    finals=[]
                    for d in range(1,21):
                        opts=payouts(s,d,quota)
                        choices=[reward+future(next_use,points,q) for reward,q in opts]
                        index=max(range(len(choices)),key=choices.__getitem__)
                        finals.append(choices[index])
                        if d==20:qp[state]=index
                    # Последний результат обязателен. Среднее повторного броска
                    # использует слой с одним уже потраченным очком.
                    retry_mean=None if not points else brews[state[0],points-1,quota][1]
                    total=0.;flags={}
                    for d,accept in enumerate(finals,1):
                        r=outcome(d,s.bonus,s.sl)
                        eligible=points>0 and r in ('fail','unst')
                        retry=eligible and ((r=='fail' or historical_unst) if policy=='historical' else retry_mean>accept+1e-12)
                        if r in ('fail','unst'):flags[r]=bool(retry)
                        total+=retry_mean if retry else accept
                    brew_value=total/20
                    brews[state]=(brew_value,sum(finals)/20);br[state]=flags
                    risk=bool(s.cat and use>CAT_STABLE)
                    if risk:
                        p=sum(check_success(d,s.bonus,INSTAB[use-CAT_STABLE-1]) for d in range(1,21))/20
                        fail_value=future(0,points,quota)
                        retry_value=None if not points else p*brews[used,points-1,quota][0]+(1-p)*future(0,points-1,quota)
                        retry=bool(points and (policy=='historical' or retry_value>fail_value+1e-12))
                        rr[state]=retry
                        earned=p*brew_value+(1-p)*(retry_value if retry else fail_value)
                    else:rr[state]=False;earned=brew_value
                    values[state]=-s.mat-(s.cat if used==0 else 0)+earned
        next_values=values;brew_policy[step]=br;risk_policy[step]=rr;quality_policy[step]=qp
    return Solution(s,capacity,policy,next_values[0,s.points,initial_quota],brew_policy,risk_policy,quality_policy)


def sample(solution, *, seed=20261010, batches=400):
    if type(batches) is not int or batches<2:raise ValueError('Нужны хотя бы две независимые истории')
    s=solution.scenario;rng=random.Random(seed);profits=[]
    for _ in range(batches):
        used=0;profit=0.;points=0;quota=-1
        for step in range(s.days*s.per_day):
            if step%s.per_day==0:points=s.points;quota=-1 if solution.capacity is None else solution.capacity
            if used==0:profit-=s.cat
            profit-=s.mat
            state=(used,points,quota);use=used+1
            if s.cat and use>CAT_STABLE:
                passed=check_success(rng.randint(1,20),s.bonus,INSTAB[use-CAT_STABLE-1])
                if not passed and solution.risk_retry[step][state]:
                    points-=1;passed=check_success(rng.randint(1,20),s.bonus,INSTAB[use-CAT_STABLE-1])
                if not passed:used=0;continue
            d=rng.randint(1,20);r=outcome(d,s.bonus,s.sl)
            if solution.brew_retry[step][used,points,quota].get(r,False):points-=1;d=rng.randint(1,20)
            opts=payouts(s,d,quota);index=solution.quality[step][used,points,quota] if d==20 else 0
            reward,quota=opts[index];profit+=reward
            used=0 if use>=s.stop or not s.cat and use>=CAT_STABLE else use
        profits.append(profit/(s.days*s.per_day))
    return dict(per_try=statistics.mean(profits),se=statistics.stdev(profits)/math.sqrt(batches),batches=batches,seed=seed)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--level',type=int,choices=range(1,11),default=3);p.add_argument('--bonus',type=int,default=5)
    p.add_argument('--days',type=int,default=14);p.add_argument('--per-day',type=int,default=4)
    p.add_argument('--points',type=int,default=2);p.add_argument('--capacity',type=int,nargs='+',default=[0,2,4])
    p.add_argument('--batches',type=int,default=400);p.add_argument('--output');a=p.parse_args()
    rows=[]
    for stop in (CAT_STABLE,CAT_STABLE+len(INSTAB)):
        for capacity in [None,*a.capacity]:
            for policy in ('historical','optimal'):
                s=potion(a.level,a.bonus,stop=stop,days=a.days,per_day=a.per_day,points=a.points)
                sol=solve(s,capacity=capacity,policy=policy);mc=sample(sol,batches=a.batches)
                exact=sol.profit/(s.days*s.per_day)
                rows.append(dict(stop=stop,capacity=capacity,policy=policy,exact_per_try=exact,mc=mc))
                print(f'stop={stop} cap={capacity} policy={policy}: {exact:.6f} MC={mc["per_try"]:.6f} se={mc["se"]:.6f}',flush=True)
    result=dict(level=a.level,bonus=a.bonus,days=a.days,per_day=a.per_day,points=a.points,assumption='daily doses; unsold inventory has no cash value or later sales',rows=rows)
    if a.output:
        with open(a.output,'w',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')


if __name__=='__main__':main()

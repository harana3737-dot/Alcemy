"""Сценарии существующих моделей: ресурс катализатора и перебросы за день.

Цены и механика берутся из sim/rules_data. Конечный горизонт оплачивает
катализатор целиком при покупке, остаток ресурса не продаёт и переносит между днями.
"""
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
import argparse
import json
import math
import random
import statistics

from rules_data import unstable_fraction, CAT_STABLE, INSTAB, HERB, P_SL, P_PRICE, CAT_PRICE
from sim import check_success, exact, potion_bonus, probs, run_catalyst
from sim_guidance import outcome, sim as guidance_mc


@dataclass(frozen=True)
class Scenario:
    bonus: int
    sl: int
    mat: float
    price: float
    cat: float
    level: int
    item_kind: str = 'potion'
    stop: int = CAT_STABLE
    points: int = 0
    per_day: int = 4
    days: int = 30
    unst_value: float = unstable_fraction(.85)
    allow_up_to_10: bool = True

    def __post_init__(self):
        potion_bonus(self.mat, self.price, item_kind=self.item_kind, level=self.level,
                     allow_up_to_10=self.allow_up_to_10)
        for name in ('bonus', 'sl', 'stop', 'points', 'per_day', 'days'):
            if type(getattr(self, name)) is not int:
                raise ValueError(f'{name}: требуется целое число')
        if not 1 <= self.stop <= CAT_STABLE + len(INSTAB):
            raise ValueError('Остановка вне ресурса катализатора')
        if self.points < 0 or self.per_day < 1 or self.days < 1:
            raise ValueError('Неверные дни, попытки или запас перебросов')
        if any(not math.isfinite(x) or x < 0 for x in (self.mat, self.price, self.cat)):
            raise ValueError('Стоимость должна быть конечной и неотрицательной')
        if not math.isfinite(self.unst_value) or not 0 <= self.unst_value <= 1:
            raise ValueError('Доля продажи нестабильного предмета должна быть от 0 до 1')

    @property
    def item(self):
        return dict(item_kind=self.item_kind, level=self.level,
                    allow_up_to_10=self.allow_up_to_10)


def potion(level, bonus, *, sale=.85, **options):
    options.setdefault("unst_value", unstable_fraction(sale))
    return Scenario(bonus, P_SL[level], level * HERB[level],
                    P_PRICE[level] * sale, CAT_PRICE[level], level, **options)


def finite_exact(s):
    """Точное ожидание по состояниям (использования, очки); без выборки бросков.

    Политика переброса совпадает с исторической sim_guidance: провал всегда,
    нестабильный результат при ok_p + un_p * u > u. Бонус качества не меняет
    эту политику. Новый результат обязателен; повторного переброса нет.
    """
    b5, b20 = potion_bonus(s.mat, s.price, **s.item)
    ok_p, un_p, _ = probs(s.bonus, s.sl)
    reroll_unst = ok_p + un_p * s.unst_value > s.unst_value

    def value(d):
        r = outcome(d, s.bonus, s.sl)
        if r == 'ok':
            return s.price + (b20 if d == 20 else b5 if d + s.bonus >= s.sl + 5 else 0)
        return s.price * s.unst_value if r == 'unst' else 0

    @lru_cache(None)
    def brewing(points):
        # Сумма вероятностей и взвешенной выручки отдельно по остатку очков.
        rows = defaultdict(lambda: [0., 0.])
        for d in range(1, 21):
            r = outcome(d, s.bonus, s.sl)
            retry = points > 0 and (r == 'fail' or r == 'unst' and reroll_unst)
            if retry:
                for second in range(1, 21):
                    rows[points - 1][0] += 1 / 400
                    rows[points - 1][1] += value(second) / 400
            else:
                rows[points][0] += 1 / 20
                rows[points][1] += value(d) / 20
        return rows

    @lru_cache(None)
    def transition(used, points):
        use = used + 1
        cost = -s.mat - (s.cat if used == 0 else 0)
        risks = [(True, points, 1.)]
        if s.cat and use > CAT_STABLE:
            p = sum(check_success(d, s.bonus, INSTAB[use-CAT_STABLE-1]) for d in range(1, 21)) / 20
            risks = [(True, points, p)]
            if points:
                risks += [(True, points-1, (1-p)*p), (False, points-1, (1-p)**2)]
            else:
                risks += [(False, points, 1-p)]
        nxt = defaultdict(float)
        reward = cost
        for success, pts, chance in risks:
            if not success:
                nxt[0, pts] += chance
                continue
            next_use = 0 if use >= s.stop or not s.cat and use >= CAT_STABLE else use
            for left, (p, revenue) in brewing(pts).items():
                nxt[next_use, left] += chance * p
                reward += chance * revenue
        return dict(nxt), reward

    states = {(0, s.points): 1.}
    total = 0.
    for _ in range(s.days):
        reset = defaultdict(float)
        for (used, _pts), probability in states.items():
            reset[used, s.points] += probability
        states = reset
        for _ in range(s.per_day):
            nxt = defaultdict(float)
            for state, probability in states.items():
                transitions, reward = transition(*state)
                total += probability * reward
                for dest, p in transitions.items():
                    nxt[dest] += probability * p
            states = nxt
    attempts = s.days * s.per_day
    return dict(profit=total, attempts=attempts, per_try=total / attempts,
                per_day=total / s.days)


def finite_mc(s, *, seed=20261010, batches=60):
    if type(batches) is not int or batches < 2:
        raise ValueError('Требуется хотя бы две независимые истории')
    rng = random.Random(seed)
    values = [guidance_mc(s.bonus, s.sl, s.mat, s.price, s.cat,
                         s.per_day, s.points, s.stop, days=s.days, u=s.unst_value,
                         rng=rng, **s.item) for _ in range(batches)]
    return dict(per_try=statistics.mean(values), se=statistics.stdev(values)/math.sqrt(batches),
                batches=batches, seed=seed)


def verify_grid(*, runs=5000, seed=20261010):
    """Фиксированные остановки: сравнение без смещения от выбора лучшей выборки.

    Ошибка отношения сумм оценена по остаткам profit - exact_ratio * attempts.
    Порог 6 стандартных ошибок — диагностика, не доказательство равенства.
    """
    if type(runs) is not int or runs < 2:
        raise ValueError('Требуется хотя бы два катализатора на точку')
    rows = []
    for level in range(1, 11):
        for bonus in (-2, 0, 4, 6, 8, 10, 12, 14, 16, 20):
            for stop in (CAT_STABLE, CAT_STABLE + len(INSTAB)):
                for ceiling in (False, True):
                    s = potion(level, bonus, stop=stop, allow_up_to_10=ceiling)
                    expected, attempts, _ = exact(s.bonus, s.sl, s.mat, s.price, s.cat,
                                                  s.stop, s.unst_value, **s.item)
                    target = expected / attempts
                    point_seed = seed + level*10000 + (bonus+2)*100 + stop*2 + ceiling
                    rng = random.Random(point_seed)
                    results = [run_catalyst(s.bonus, s.sl, s.mat, s.price, s.cat,
                                           s.stop, s.unst_value, rng=rng, **s.item) for _ in range(runs)]
                    mean_tries = statistics.mean(t for _, t, _ in results)
                    observed = statistics.mean(p for p, _, _ in results) / mean_tries
                    residuals = [p-target*t for p,t,_ in results]
                    se = statistics.stdev(residuals)/math.sqrt(runs)/mean_tries
                    delta = observed-target
                    z = abs(delta)/se if se else (0. if abs(delta)<1e-9 else math.inf)
                    rows.append(dict(level=level, bonus=bonus, stop=stop, allow_up_to_10=ceiling,
                                     exact=target, mc=observed, se=se, z=z, seed=point_seed))
    return dict(runs=runs, seed=seed, points=len(rows), max_z=max(r['z'] for r in rows),
                passed=all(r['z']<=6 for r in rows), rows=rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--grid', action='store_true')
    p.add_argument('--runs', type=int, default=5000)
    p.add_argument('--level', type=int, choices=range(1, 11), default=3)
    p.add_argument('--sale', type=float, default=.85, help='Примерная ставка обычной продажи, например 0.90')
    p.add_argument('--bonus', type=int, default=5)
    p.add_argument('--days', type=int, default=30)
    p.add_argument('--per-day', type=int, default=4)
    p.add_argument('--points', type=int, nargs='+', default=[0, 2, 5])
    p.add_argument('--seed', type=int, default=20261010)
    p.add_argument('--output')
    a = p.parse_args()
    if a.grid:
        result = verify_grid(runs=a.runs, seed=a.seed)
    else:
        rows=[]
        for stop in (CAT_STABLE, CAT_STABLE+len(INSTAB)):
            for points in a.points:
                s=potion(a.level,a.bonus,sale=a.sale,stop=stop,points=points,days=a.days,per_day=a.per_day)
                rows.append(dict(stop=stop,points=points,exact=finite_exact(s),mc=finite_mc(s,seed=a.seed)))
        result=dict(level=a.level,bonus=a.bonus,sale=a.sale,days=a.days,per_day=a.per_day,rows=rows)
    if a.output:
        with open(a.output,'w',encoding='utf-8') as f:
            json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False,allow_nan=False))
    if a.grid and not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

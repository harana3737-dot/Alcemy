"""Волшебное указание в дни алхимии: запас класса плюс переработка ячеек.

Одновременно хранится не больше уровня класса. points — суммарный доступный
расход между отдыхами: ячейки переводятся по мере расхода, без переполнения.
"""
from functools import lru_cache
from sim import probs, p_bonus

SLOTS = {
    5:(4,3,2), 6:(4,3,3), 7:(4,3,3,1), 8:(4,3,3,2),
    9:(4,3,3,3,1), 10:(4,3,3,3,2), 11:(4,3,3,3,2,1),
    12:(4,3,3,3,2,1), 13:(4,3,3,3,2,1,1), 14:(4,3,3,3,2,1,1),
    15:(4,3,3,3,2,1,1,1), 16:(4,3,3,3,2,1,1,1),
    17:(4,3,3,3,2,1,1,1,1), 18:(4,3,3,3,3,1,1,1,1),
    19:(4,3,3,3,3,2,1,1,1), 20:(4,3,3,3,3,2,2,1,1),
}
EXAMPLE_CLASS = {1:3,2:5,3:6,4:7,5:9,6:10,7:11,8:13,9:17,10:20}


def budget(level, *, convert_slots=True, reserve=0):
    if type(level) is not int or not 1 <= level <= 20:
        raise ValueError('Уровень чародея должен быть от 1 до 20')
    if type(reserve) is not int or reserve < 0:
        raise ValueError('Резерв не может быть отрицательным')
    total = 0 if level < 5 else level + (sum(i*n for i,n in enumerate(SLOTS[level],1)) if convert_slots else 0)
    if reserve > total:
        raise ValueError('Резерв больше доступного запаса')
    return total-reserve


def chances(bonus, dc, guidance=True):
    ok, un, fail = probs(bonus, dc)
    factor = 2-ok if guidance else 1
    return ok*factor, un*(1-ok) if guidance else un, fail*(1-ok) if guidance else fail


def quality(bonus, dc, guidance=True):
    ok = probs(bonus, dc)[0]
    factor = 2-ok if guidance else 1
    return tuple(p*factor for p in p_bonus(bonus,dc))


@lru_cache(None)
def sales(bonus, dc, mat, price, cat, unstable, hours, *, item_kind, level,
          class_level=5, batch=1, days=30, convert_slots=True, reserve=0):
    """Конечные дневные ресурсы, целый катализатор и перенос его остатка.

    Дневной объём — 8 часов; прибыль усредняется за 30 дней производства.
    На продаже дефект перебрасывается, только если это выгодно по политике
    общего scenario_engine. Дни подразумевают состоявшиеся долгие отдыхи.
    """
    from scenario_engine import Scenario, finite_exact
    from rules_data import CAT_STABLE, INSTAB
    attempts=int(8/hours)*batch
    points=min(budget(class_level,convert_slots=convert_slots,reserve=reserve), attempts*(2 if cat else 1))
    stable=10 if level==10 and cat else CAT_STABLE
    candidates=[]
    for stop in range(stable,stable+len(INSTAB)+1) if cat else (stable,):
        s=Scenario(bonus,dc,mat,price,cat,level,item_kind=item_kind,stop=stop,stable_uses=stable,
                   points=points,per_day=attempts,days=days,unst_value=unstable)
        r=finite_exact(s)
        candidates.append(dict(r,stop=stop,per_hour=r['per_day']/8))
    return max(candidates,key=lambda r:r['per_try'])

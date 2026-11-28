"""Restricted deterministic replay of ordinary healing brewing.
No risky catalyst use, no sales, no automatic rest, no research.
Money is not inventory: purchases are explicit external events.
"""
from dataclasses import dataclass, field
from rules_data import MB, NEED, P_SL, CAT_ORDER_BY_LEVEL, normal_brewing_allowed, proficiency
from sim_plan import batch_p

@dataclass
class State:
    level: int
    mastery: int
    practice: int
    lab: int
    points: int
    herbs: dict = field(default_factory=dict)
    catalysts: dict = field(default_factory=dict)
    known: set = field(default_factory=set)
    hours: int = 0
    intelligence: int = 0
    products: dict = field(default_factory=dict)

def brew(s, level, rolls, retries=None):
    """Rolls are supplied by caller; replay is deterministic.
    Catalyst inventory is stable uses, not number of objects.
    Quality policy: save herbs on 5+ and natural 20.
    """
    retries = retries or {}
    if level not in s.known or not normal_brewing_allowed(level,s.mastery,s.lab):
        raise ValueError("Recipe or equipment unavailable")
    cap = batch_p(s.mastery,level) if level <= 5 else 1
    n = len(rolls)
    if not 1 <= n <= cap:
        raise ValueError("Invalid batch size")
    if any(type(d) is not int or not 1 <= d <= 20 for d in [*rolls,*retries.values()]):
        raise ValueError("Invalid die")
    b = proficiency(s.level)+MB[s.mastery]+s.lab+s.intelligence
    dc = P_SL[level]
    if len(retries)>s.points or (retries and s.level<5):
        raise ValueError("Insufficient guidance")
    for i in retries:
        if not 0<=i<n or rolls[i]==20 or (rolls[i]!=1 and rolls[i]+b>=dc):
            raise ValueError("Invalid retry")
    order = CAT_ORDER_BY_LEVEL[level]
    if s.herbs.get(level,0)<n*level or (order and s.catalysts.get(order,0)<n):
        raise ValueError("Insufficient materials")
    gain=0
    for i,original in enumerate(rolls):
        d=retries.get(i,original)
        ok=d==20 or (d!=1 and d+b>=dc)
        unstable=not ok and d!=1 and d+b>=dc-4
        if not (ok and (d==20 or d+b>=dc+5)):
            s.herbs[level]-=level
        if order:
            s.catalysts[order]-=1
        if ok or unstable:
            key=(level,"stable" if ok else "unstable")
            s.products[key]=s.products.get(key,0)+1
        if ok and level==s.mastery:
            gain+=2 if d==20 else 1
    s.points-=len(retries)
    s.hours+=2
    if s.mastery<10:
        s.practice+=gain
        if s.practice>=NEED[s.mastery]:
            s.mastery+=1
            s.practice=0
    return s

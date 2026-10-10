"""Недельная варка Талиса: цена единицы (часы и золото) по ступеням мастерства и доход в час на продажу.
Поверх sim.py, sim_week.py и sim_volume.py; правила не меняются. Заряды и склянки I–V по цене, травам и СЛ
совпадают с чернилами того же уровня (справочник цен), поэтому доход в час у них один."""

from rules_data import unstable_fraction, CAT_STABLE, ROM, BATCH_T, elixir_batch
import random as _random
from sim_week import TALIS
import sim_volume as volume
from sim import HERB, P_SL, P_PRICE, CAT_PRICE, INK, probs, scenario, p_bonus
from sim import INSTAB as INSTAB  # Public table retained for existing callers.

# Доз в партии зелья (6.2): мастерство → (1.1, 2.2, 3.3, 4.4, 5.5); 6.6+ — по одной


def batch_p(m, l):
    if m not in BATCH_T or not 1 <= l <= 10:
        raise ValueError('Мастерство и уровень должны быть от 1 до 10')
    row = BATCH_T[m]
    return row[l - 1] if l <= len(row) else 1


def ink_set(m, k):
    """один годный набор чернил уровня k (I–V) на мастерстве m: часы и золото; нестабильные годятся (−2, 10.4)"""
    price, herbs, ess, sl, cl, h = INK[ROM[k]]
    sl += 5 + k - m if k > m else 0
    ok, un, _ = probs(TALIS[m], sl)
    t = 1 / (ok + un)
    return t * h, t * (herbs + ess + CAT_PRICE[cl] / CAT_STABLE), ok / (ok + un)


def elixir(m, l):
    """одна доза эликсира-эффекта уровня l ≤ min(m, 5) партией (М − ур.) + 2, не больше 3 (I–II) / 2 (III–V)"""
    size = elixir_batch(m, l)
    ok, un, _ = probs(TALIS[m], P_SL[l] + 2)
    hours = (2 if l <= 2 else 4) / size / ok
    return hours, (l * HERB[l] + HERB[l] + CAT_PRICE[l] / CAT_STABLE) / ok


def potion(m, l):
    ok, un, _ = probs(TALIS[m], P_SL[l])
    p5, _ = p_bonus(TALIS[m], P_SL[l])
    return 2 / batch_p(m, l) / ok, (l * HERB[l] * (1 - p5) + CAT_PRICE[l] / CAT_STABLE) / ok


def per_hour(m, *, rng=None):
    b = TALIS[m]
    pot = max(scenario(b, P_SL[l], l * HERB[l], P_PRICE[l] * .85, CAT_PRICE[l], unstable_fraction(.85), 2, item_kind='potion', level=l)["per_try"] * batch_p(m, l) / 2
              for l in range(1, min(m, 10) + 1))
    best_ink = max((scenario(b, INK[ROM[k]][3], INK[ROM[k]][1] + INK[ROM[k]][2], INK[ROM[k]][0] * .85,
                             CAT_PRICE[INK[ROM[k]][4]], unstable_fraction(.85), INK[ROM[k]][5], item_kind='ink', level=k)["per_day"] / 8, ROM[k]) for k in range(1, min(m, 5) + 1))
    vol = None
    if m >= 6:
        res = []
        for l in range(6, min(m, 8) + 1):
            price = volume.CHG[l]
            st = volume.volume_stats(b, l, price, price / 3 + volume.ESS[l], False, 6000, rng=rng)
            res.append((st["profit"] / st["hours"], ROM[l], st["hours"]))
        vol = max(res)
    return dict(pot=pot, ink=best_ink, vol=vol)




def week(m, ink_k, kit_l, heal_l, hours, sets=2.5, kit_n=3, heal_n=4, *, income=None):
    """Ожидаемые затраты заказа; fits_expected_budget не гарантирует срок."""
    if min(hours, sets, kit_n, heal_n) < 0:
        raise ValueError('Часы и количества не могут быть отрицательными')
    ih, ig, ist = ink_set(m, ink_k); eh, eg = elixir(m, kit_l); ph, pg = potion(m, heal_l)
    fixed = sets * ih + kit_n * eh + heal_n * ph
    ph_best = per_hour(m) if income is None else income
    best = max(ph_best["pot"], ph_best["ink"][0], ph_best["vol"][0] if ph_best["vol"] else 0)
    free = max(0, hours - fixed)
    return dict(ink=(sets * ih, sets * ig, ist), kit=(kit_n * eh, kit_n * eg), heal=(heal_n * ph, heal_n * pg),
                fixed=fixed, free=free, sale=free * best, best=best,
                budget_hours=hours, fits_expected_budget=fixed <= hours + 1e-9,
                shortfall_hours=max(0, fixed - hours), estimate_only=True)


if __name__ == "__main__":
    rng = _random.Random(90)
    for m in range(2, 10):
        rate = per_hour(m, rng=rng)
        print("M", m, "bonus", TALIS[m], {k: (round(v[0], 1) if isinstance(v, tuple) else round(v, 1)) if v else None for k, v in rate.items()},
              "vol", rate["vol"] and (rate["vol"][1], round(rate["vol"][2], 1)), "inkbest", rate["ink"][1])
        print("   ink sets k:", {ROM[k]: tuple(round(x, 2) for x in ink_set(m, k)) for k in range(1, 6)})
        print("   elixir l:", {ROM[l]: tuple(round(x, 2) for x in elixir(m, l)) for l in range(1, min(m, 5) + 1)})
        print("   potion l:", {f"{l}.{l}": tuple(round(x, 2) for x in potion(m, l)) for l in range(1, min(m, 9) + 1)})

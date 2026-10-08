"""Недельная варка Талиса: цена единицы (часы и золото) по ступеням мастерства и доход в час на продажу.
Поверх sim.py, sim_week.py и sim_volume.py; правила не меняются. Заряды и склянки I–V по цене, травам и СЛ
совпадают с чернилами того же уровня (справочник цен), поэтому доход в час у них один."""
import sys
sys.argv = ["x", "10"]
exec(open(__file__.replace("sim_plan.py", "sim.py"), encoding="utf-8").read().split("# проверка точного расчёта")[0])
_w = {"__file__": __file__.replace("sim_plan.py", "sim_week.py")}
exec(open(_w["__file__"], encoding="utf-8").read(), _w)
_v = {"__file__": __file__.replace("sim_plan.py", "sim_volume.py")}
exec(open(_v["__file__"], encoding="utf-8").read(), _v)
TALIS = _w["TALIS"]
ROM = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
# Доз в партии зелья (6.2): мастерство → (1.1, 2.2, 3.3, 4.4, 5.5); 6.6+ — по одной
BATCH_T = {1: (2,), 2: (4, 2), 3: (6, 5, 4), 4: (8, 6, 5, 4), 5: (10, 8, 6, 5, 4),
           6: (10, 10, 8, 6, 5), 7: (10, 10, 10, 8, 6), 8: (10, 10, 10, 10, 8),
           9: (10, 10, 10, 10, 10), 10: (10, 10, 10, 10, 10)}


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
    return t * h, t * (herbs + ess + CAT_PRICE[cl] / 5), ok / (ok + un)


def elixir(m, l):
    """одна доза эликсира-эффекта уровня l ≤ min(m, 5) партией (М − ур.) + 2, не больше 3 (I–II) / 2 (III–V)"""
    size = min(m - l + 2, 3 if l <= 2 else 2)
    ok, un, _ = probs(TALIS[m], P_SL[l] + 2)
    hours = (2 if l <= 2 else 4) / size / ok
    return hours, (l * HERB[l] + HERB[l] + CAT_PRICE[l] / 5) / ok


def potion(m, l):
    ok, un, _ = probs(TALIS[m], P_SL[l])
    p5, _ = p_bonus(TALIS[m], P_SL[l])
    return 2 / batch_p(m, l) / ok, (l * HERB[l] * (1 - p5) + CAT_PRICE[l] / 5) / ok


def per_hour(m):
    b = TALIS[m]
    pot = max(scenario(b, P_SL[l], l * HERB[l], P_PRICE[l] * .85, CAT_PRICE[l], .5, 2)["per_try"] * batch_p(m, l) / 2
              for l in range(1, min(m, 10) + 1))
    best_ink = max((scenario(b, INK[ROM[k]][3], INK[ROM[k]][1] + INK[ROM[k]][2], INK[ROM[k]][0] * .85,
                             CAT_PRICE[INK[ROM[k]][4]], .5, INK[ROM[k]][5])["per_day"] / 8, ROM[k]) for k in range(1, min(m, 5) + 1))
    vol = None
    if m >= 6:
        res = []
        for l in range(6, min(m, 8) + 1):
            price = _v["CHG"][l]
            st = _v["volume_stats"](b, l, price, price / 3 + _v["ESS"][l], False, 6000)
            res.append((st["profit"] / st["hours"], ROM[l], st["hours"]))
        vol = max(res)
    return dict(pot=pot, ink=best_ink, vol=vol)


if __name__ == "__main__":
    for m in range(2, 10):
        print("M", m, "bonus", TALIS[m], {k: (round(v[0], 1) if isinstance(v, tuple) else round(v, 1)) if v else None for k, v in per_hour(m).items()},
              "vol", per_hour(m)["vol"] and (per_hour(m)["vol"][1], round(per_hour(m)["vol"][2], 1)), "inkbest", per_hour(m)["ink"][1])
        print("   ink sets k:", {ROM[k]: tuple(round(x, 2) for x in ink_set(m, k)) for k in range(1, 6)})
        print("   elixir l:", {ROM[l]: tuple(round(x, 2) for x in elixir(m, l)) for l in range(1, min(m, 5) + 1)})
        print("   potion l:", {f"{l}.{l}": tuple(round(x, 2) for x in potion(m, l)) for l in range(1, min(m, 9) + 1)})


def week(m, ink_k, kit_l, heal_l, hours, sets=2.5, kit_n=3, heal_n=4):
    """Ожидаемые затраты заказа; fits_expected_budget не гарантирует срок."""
    if min(hours, sets, kit_n, heal_n) < 0:
        raise ValueError('Часы и количества не могут быть отрицательными')
    ih, ig, ist = ink_set(m, ink_k); eh, eg = elixir(m, kit_l); ph, pg = potion(m, heal_l)
    fixed = sets * ih + kit_n * eh + heal_n * ph
    ph_best = per_hour(m)
    best = max(ph_best["pot"], ph_best["ink"][0], ph_best["vol"][0] if ph_best["vol"] else 0)
    free = max(0, hours - fixed)
    return dict(ink=(sets * ih, sets * ig, ist), kit=(kit_n * eh, kit_n * eg), heal=(heal_n * ph, heal_n * pg),
                fixed=fixed, free=free, sale=free * best, best=best,
                budget_hours=hours, fits_expected_budget=fixed <= hours + 1e-9,
                shortfall_hours=max(0, fixed - hours), estimate_only=True)

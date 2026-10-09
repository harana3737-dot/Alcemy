"""Монте-Карло экономики зелий и чернил по правилам v0.3 + решение мастера:
провал тратит травы и применение катализатора; партия — одно применение на дозу."""

from rules_data import HERB, P_SL, P_PRICE, CAT_PRICE, INSTAB, INK
import random as _random
import json
import sys

random = _random.Random(20261002)

N_CAT = 20000   # катализаторов на сценарий


# чернила: уровень → (цена набора, травы матрицы, эссенция, СЛ, порядок катализатора по уровню-аналогу, часы)


def check_success(d, bonus, sl):
    """Натуральные 1/20 имеют приоритет над итогом (раздел 2, Ж-94)."""
    return d == 20 or d != 1 and d + bonus >= sl


def roll(bonus, sl, with_d=False, *, rng=None):
    """→ 'ok' (успех, в т.ч. 5+ и нат. 20), 'unst' (провал 1–4), 'fail' (провал 5+ / нат. 1); with_d — ещё и бросок"""
    d = (random if rng is None else rng).randint(1, 20)
    if d == 1:
        r = "fail"
    elif check_success(d, bonus, sl):
        r = "ok"
    else:
        r = "unst" if sl - (d + bonus) <= 4 else "fail"
    return (r, d) if with_d else r


# Бонусы 7.7 у зелий на продажу: на 5+ — экономия трав, на 20 — лучшее из «ещё одно», «выше уровнем» (до 9.9)
# и «два бонуса» (= экономия). Зелье опознаётся по стоимости трав (уровень × цена травы) — у чернил она другая.
POT_LVL = {l * HERB[l]: l for l in HERB}


def potion_bonus(mat, price):
    l = POT_LVL.get(mat)
    if l is None:
        return 0.0, 0.0
    up = price / P_PRICE[l] * P_PRICE[l + 1] - price if l <= 9 else 0.0
    return mat, max(price, up, mat)


def p_bonus(bonus, sl):
    """доли бросков: успех на 5+ (без натуральной 20) и натуральная 20"""
    return sum(1 for d in range(2, 20) if d + bonus >= sl + 5) / 20, 1 / 20


def run_catalyst(bonus, sl, mat_cost, price, cat_price, stop_after, unst_value, *, rng=None):
    """Один катализатор от покупки до списания. Возвращает (прибыль, попыток, успехов)."""
    rng = random if rng is None else rng
    b5, b20 = potion_bonus(mat_cost, price)
    profit, tries, oks = -cat_price, 0, 0
    for use in range(1, stop_after + 1):
        if use > 5 and cat_price:
            if not check_success(rng.randint(1, 20), bonus, INSTAB[use - 6]):
                profit -= mat_cost
                tries += 1
                break
        profit -= mat_cost
        tries += 1
        r, d = roll(bonus, sl, True, rng=rng)
        if r == "ok":
            profit += price
            oks += 1
            profit += b20 if d == 20 else b5 if d + bonus >= sl + 5 else 0
        elif r == "unst":
            profit += price * unst_value
    return profit, tries, oks


def probs(bonus, sl):
    ok = un = fa = 0
    for d in range(1, 21):
        if d == 1: fa += 1
        elif d == 20 or d + bonus >= sl: ok += 1
        elif sl - (d + bonus) <= 4: un += 1
        else: fa += 1
    return ok / 20, un / 20, fa / 20


def exact(bonus, sl, mat, price, cat, stop, unst_value):
    ok, un, _ = probs(bonus, sl)
    p5, p20 = p_bonus(bonus, sl)
    b5, b20 = potion_bonus(mat, price)
    v = ok * price + un * price * unst_value - mat + p5 * b5 + p20 * b20
    reach, E, T = 1.0, -cat, 0.0
    for use in range(1, stop + 1):
        if use > 5 and cat:
            s = probs(bonus, INSTAB[use - 6])[0]
            E += reach * (s * v - (1 - s) * mat); T += reach
            reach *= s
        else:
            E += reach * v; T += reach
    return E, T, ok


def scenario(bonus, sl, mat, price, cat, unst_value, hours):
    best = None
    for stop in ([5, 6, 7, 8, 9, 10] if cat else [5]):
        E, T, ok = exact(bonus, sl, mat, price, cat, stop, unst_value)
        res = dict(stop=stop, per_try=E / T, ok_rate=ok, per_day=E / T * (8 / hours))
        if best is None or res["per_try"] > best["per_try"] + 1e-9:
            best = res
    return best


def scenario_mc(bonus, sl, mat, price, cat, unst_value, hours, *, rng=None):
    best = None
    for stop in ([5, 6, 7, 8, 9, 10] if cat else [5]):
        P = T = O = 0
        for _ in range(N_CAT):
            p, t, o = run_catalyst(bonus, sl, mat, price, cat, stop, unst_value, rng=rng)
            P += p; T += t; O += o
        res = dict(stop=stop, per_try=P / T, ok_rate=O / T, per_day=P / T * (8 / hours))
        if best is None or res["per_try"] > best["per_try"]:
            best = res
    return best


def breakeven(sl, mat, price, cat, unst_value, hours):
    for b in range(-2, 25):
        if scenario(b, sl, mat, price, cat, unst_value, hours)["per_try"] > 0:
            return b
    return None


def main():
    global N_CAT
    N_CAT = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    random.seed(20261002)
    # проверка точного расчёта Монте-Карло
    for (b, l) in [(6, 4), (8, 6), (10, 8)]:
        a = scenario(b, P_SL[l], l * HERB[l], P_PRICE[l] * .85, CAT_PRICE[l], .5, 2)
        m = scenario_mc(b, P_SL[l], l * HERB[l], P_PRICE[l] * .85, CAT_PRICE[l], .5, 2)
        print("check", l, b, round(a["per_try"], 2), a["stop"], "MC", round(m["per_try"], 2), m["stop"], flush=True)
    out = {"potions": {}, "inks": {}}
    BONUSES = [4, 6, 8, 10, 12]
    for lvl in range(1, 11):
        mat = lvl * HERB[lvl]
        row = {"mat": mat, "cat_use": CAT_PRICE[lvl] / 5, "sl": P_SL[lvl], "price": P_PRICE[lvl]}
        for sale, key in [(0.85, "s85"), (1.0, "s100")]:
            pr = P_PRICE[lvl] * sale
            row[key] = {str(b): scenario(b, P_SL[lvl], mat, pr, CAT_PRICE[lvl], 0.5, 2) for b in BONUSES}
            row[key + "_be"] = breakeven(P_SL[lvl], mat, pr, CAT_PRICE[lvl], 0.5, 2)
            row[key + "_be_unst0"] = breakeven(P_SL[lvl], mat, pr, CAT_PRICE[lvl], 0.0, 2)
        out["potions"][lvl] = row
        print("potion", lvl, row["s85_be"], {b: round(v["per_try"], 1) for b, v in row["s85"].items()}, flush=True)

    for name, (price, herbs, ess, sl, catlvl, hours) in INK.items():
        mat = herbs + ess
        row = {"mat": mat, "sl": sl, "price": price, "hours": hours}
        for sale, key in [(0.85, "s85"), (1.0, "s100")]:
            pr = price * sale
            row[key] = {str(b): scenario(b, sl, mat, pr, CAT_PRICE[catlvl], 0.5, hours) for b in BONUSES}
            row[key + "_be"] = breakeven(sl, mat, pr, CAT_PRICE[catlvl], 0.5, hours)
        out["inks"][name] = row
        print("ink", name, row["s85_be"], {b: round(v["per_day"]) for b, v in row["s85"].items()}, flush=True)

    json.dump(out, open("sim.json", "w"), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()

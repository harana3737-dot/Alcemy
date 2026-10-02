"""Монте-Карло экономики зелий и чернил по правилам v0.3 + решение мастера:
провал тратит травы и применение катализатора; партия — одно применение на дозу."""
import random, json, sys

random.seed(20261002)
N_CAT = int(sys.argv[1]) if len(sys.argv) > 1 else 20000   # катализаторов на сценарий

HERB = {1: .1, 2: .5, 3: 1, 4: 2, 5: 4, 6: 8, 7: 16, 8: 32, 9: 64, 10: 128}
P_SL = {1: 10, 2: 10, 3: 11, 4: 13, 5: 15, 6: 17, 7: 19, 8: 21, 9: 23, 10: 25}
P_PRICE = {1: 1.65, 2: 4.5, 3: 18.4, 4: 26.4, 5: 43.75, 6: 135.2, 7: 228.15, 8: 719.6, 9: 1210.75, 10: 3435}
CAT_PRICE = {1: 0, 2: 0, 3: 70, 4: 70, 5: 70, 6: 350, 7: 350, 8: 1750, 9: 1750, 10: 7500}
INSTAB = [10, 12, 14, 16, 18]              # СЛ проверки перед 6-м…10-м применением

# чернила: уровень → (цена набора, травы матрицы, эссенция, СЛ, порядок катализатора по уровню-аналогу, часы)
INK = {
    "I":   (30, 10, HERB[1], 12, 1, 2), "II": (120, 40, HERB[2], 12, 2, 2), "III": (300, 100, HERB[3], 13, 3, 4),
    "IV": (1200, 400, HERB[4], 15, 4, 4), "V": (2500, 2500 / 3, HERB[5], 17, 5, 4), "VI": (7500, 2500, HERB[6], 19, 6, 8),
}


def roll(bonus, sl):
    """→ 'ok' (успех, в т.ч. 5+ и нат. 20), 'unst' (провал 1–4), 'fail' (провал 5+ / нат. 1)"""
    d = random.randint(1, 20)
    if d == 1:
        return "fail"
    if d == 20:
        return "ok"
    t = d + bonus
    if t >= sl:
        return "ok"
    return "unst" if sl - t <= 4 else "fail"


def run_catalyst(bonus, sl, mat_cost, price, cat_price, stop_after, unst_value):
    """Один катализатор от покупки до списания. Возвращает (прибыль, попыток, успехов)."""
    profit, tries, oks = -cat_price, 0, 0
    for use in range(1, stop_after + 1):
        if use > 5 and cat_price:
            if random.randint(1, 20) + bonus < INSTAB[use - 6]:   # катализатор испорчен вместе с предметом
                profit -= mat_cost
                tries += 1
                break
        profit -= mat_cost
        tries += 1
        r = roll(bonus, sl)
        if r == "ok":
            profit += price
            oks += 1
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
    v = ok * price + un * price * unst_value - mat
    reach, E, T = 1.0, -cat, 0.0
    for use in range(1, stop + 1):
        if use > 5 and cat:
            s = min(1, max(0, (21 + bonus - INSTAB[use - 6]) / 20))
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


def scenario_mc(bonus, sl, mat, price, cat, unst_value, hours):
    best = None
    for stop in ([5, 6, 7, 8, 9, 10] if cat else [5]):
        P = T = O = 0
        for _ in range(N_CAT):
            p, t, o = run_catalyst(bonus, sl, mat, price, cat, stop, unst_value)
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

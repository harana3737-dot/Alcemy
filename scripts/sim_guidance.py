"""Талис 5 ур.: «Волшебное указание» (TCE, чародей 5): проваленную проверку характеристики
можно перебросить за 1 единицу чародейства, новый результат обязателен. 5 единиц на долгий отдых."""
import random as _random
from sim import HERB, P_SL, P_PRICE, CAT_PRICE, INSTAB, INK, check_success, roll, probs, scenario, p_bonus, potion_bonus

random = _random.Random(5)


def outcome(d, bonus, sl):
    if d == 1: return "fail"
    if d == 20 or d + bonus >= sl: return "ok"
    return "unst" if sl - (d + bonus) <= 4 else "fail"


def sim(bonus, sl, mat, price, cat, per_day, points, stop, days=100000, u=.5, *, rng=None):
    ok_p, un_p, _ = probs(bonus, sl)
    reroll_unst = ok_p + un_p * u > u          # перебрасывать нестабильное, только если это выгодно
    rng = random if rng is None else rng
    b5, b20 = potion_bonus(mat, price)
    profit = 0.0; tries = 0; use = 0
    for _ in range(days):
        pts = points
        for _ in range(per_day):
            if use == 0:
                profit -= cat
            use += 1
            profit -= mat; tries += 1
            if use > 5 and cat:                 # проверка нестабильности — тоже проверка характеристики
                ok = check_success(rng.randint(1, 20), bonus, INSTAB[use - 6])
                if not ok and pts:
                    pts -= 1; ok = check_success(rng.randint(1, 20), bonus, INSTAB[use - 6])
                if not ok:
                    use = 0; continue
            d = rng.randint(1, 20); r = outcome(d, bonus, sl)
            if pts and (r == "fail" or (r == "unst" and reroll_unst)):
                pts -= 1; d = rng.randint(1, 20); r = outcome(d, bonus, sl)
            profit += price if r == "ok" else price * u if r == "unst" else 0
            if r == "ok":                       # бонусы 7.7 у зелий: 5+ — экономия трав, 20 — лучший вариант
                profit += b20 if d == 20 else b5 if d + bonus >= sl + 5 else 0
            if use >= stop or not cat and use >= 5:
                use = 0
    return profit / tries


def build_tables(*, seed=5, days=100000):
    rng = _random.Random(seed)
    B, MAST = 5, 3
    rows = []
    items = [(f"зелье {l}.{l}" + (" (выше мастерства)" if l > MAST else ""), P_SL[l] + (5 + l - MAST if l > MAST else 0), l * HERB[l], P_PRICE[l] * .85, CAT_PRICE[l], 4) for l in range(1, 5)]
    for n, ml in [("I", 1), ("II", 2), ("III", 3), ("IV", 4)]:
        price, herbs, ess, sl, cl, h = INK[n]
        items.append((f"чернила {n}" + (" (выше мастерства)" if ml > MAST else ""), sl + (5 + ml - MAST if ml > MAST else 0), herbs + ess, price * .85, CAT_PRICE[cl], 8 // h))
    for name, sl, mat, price, cat, per_day in items:
        res = []
        for pts in (0, 2, 5):
            best = max(sim(B, sl, mat, price, cat, per_day, pts, stop, days=days, rng=rng) for stop in ((5, 10) if cat else (5,)))
            res.append(best)
        rows.append((name, sl, per_day, res))

    return dict(rows=rows, rng_state=rng.getstate())


if __name__ == "__main__":
    print(build_tables()["rows"])

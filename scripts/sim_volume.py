"""Долгая варка VI+ объёмом работы (правила, 6.3) и помощник (6.4). Монте-Карло.
Подход 2 часа: успех — +итог; 5+ — +итог и метка; 10+ — +итог и 2 метки; провал 1–4 — +½ итога и заминка
(3 заминки = дефект); провал 5+ — 0 и дефект; нат. 20 — прогресс ×2 и метка; нат. 1 — 0, −d20, дефект.
Завершение — проверка с модификатором (метки − дефекты), от −2 до +2. Помощник: +2 к прогрессу подхода
и +2 к завершающей проверке."""

from rules_data import unstable_fraction, CAT_STABLE, VOL, SL_E, ESS, CAT_E, MB, PLAYER_LAB as LAB, INK_PRICES
import random as _random
from sim import HERB, P_SL, P_PRICE, CAT_PRICE, INSTAB, INK, check_success, roll, probs, scenario, p_bonus, potion_bonus

random = _random.Random(90)



def volume_run(bonus, sl, vol, helper, max_approaches=200, *, rng=None):
    """Возвращает завершённую варку; лимит без прогресса — явный тайм-аут."""
    if vol <= 0 or max_approaches <= 0:
        raise ValueError('Объём и лимит подходов должны быть положительными')
    rng = random if rng is None else rng
    prog = marks = hitch = defects = n = 0
    while prog < vol:
        n += 1
        d = rng.randint(1, 20); t = d + bonus + (2 if helper else 0)   # помощник: +2 к каждой проверке подхода (Ж-96)
        if d == 20:
            prog += 2 * t; marks += 1
        elif d == 1:
            prog = max(0, prog - rng.randint(1, 20)); defects += 1
        elif t >= sl:
            prog += t; marks += 2 if t - sl >= 10 else 1 if t - sl >= 5 else 0
        elif sl - t <= 4:
            prog += t / 2; hitch += 1
            if hitch == 3:
                hitch = 0; defects += 1
        else:
            defects += 1
        if n >= max_approaches and prog < vol:
            raise TimeoutError(f'Варка не завершена: {prog} из {vol}, подходов {n}')
    mod = max(-2, min(2, marks - defects))
    return n, roll(bonus + mod + (2 if helper else 0), sl, rng=rng)


def volume_stats(bonus, lvl, price, mat, helper=False, runs=20000, *, rng=None, sale=.85):
    sl, vol = SL_E[lvl], VOL[lvl]
    cat = CAT_E[lvl] / CAT_STABLE                  # пять стабильных применений, без риска
    A = P = OK = 0
    for _ in range(runs):
        n, r = volume_run(bonus, sl, vol, helper, rng=rng)
        A += n
        P += price * sale if r == "ok" else price * sale * unstable_fraction(sale) if r == "unst" else 0
        OK += r == "ok"
    apr = A / runs
    profit = P / runs - mat - cat
    return dict(approaches=apr, hours=apr * 2, ok=OK / runs, profit=profit, per_day=profit / (apr * 2 / 8))


def typ(l):
    return 7 + MB[l] + LAB[l]


# заряды и склянки = чернила того же уровня: цена набора, травы 1/3, эссенция уровня
CHG = {l: INK_PRICES[l] for l in VOL}
EFF = {6: ("Невидимость", 250), 7: ("Полёт", 500), 8: ("Скорость", 1750)}
ROMN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"]

def build_tables(*, seed=90, runs=20000):
    """Reference tables and stream position for reproducible downstream reports."""
    rng = _random.Random(seed)
    vol_rows = []
    for l in (6, 7, 8):
        b = typ(l)
        items = [(f"заряд, склянка или чернила {ROMN[l]}", CHG[l], CHG[l] / 3 + ESS[l]),
                 (f"эликсир-эффект {ROMN[l]} ({EFF[l][0]})", EFF[l][1], l * HERB[l] + ESS[l])]
        for name, price, mat in items:
            s0 = volume_stats(b, l, price, mat, False, runs, rng=rng)
            s1 = volume_stats(b, l, price, mat, True, runs, rng=rng)
            vol_rows.append((name, l, b, price, mat, s0, s1))

    # помощник на обычных варках: +2 к проверке, цена по мастерству помощника (не ниже мастерства − 2)
    help_rows = []
    cases = [("Талис сейчас: зелье 2.2", 4, 2, 2), ("Талис сейчас: чернила I", 4, 2, "I"), ("Талис сейчас: чернила II", 4, 2, "II"),
             ("зелье 4.4, типичный бонус", typ(4), 4, 4), ("зелье 5.5, типичный бонус", typ(5), 5, 5),
             ("чернила IV, бонус +8", 8, 4, "IV"), ("чернила V, бонус +8", 8, 5, "V")]
    for name, b, mast, it in cases:
        cost = 2 if mast - 2 <= 2 else 5 if mast - 2 <= 5 else 15
        if isinstance(it, int):
            l = it; args = (P_SL[l], l * HERB[l], P_PRICE[l] * .85, CAT_PRICE[l], unstable_fraction(.85), 2)
        else:
            price, herbs, ess, sl, cl, h = INK[it]; args = (sl, herbs + ess, price * .85, CAT_PRICE[cl], unstable_fraction(.85), h)
        item_kind, item_level = ('potion', it) if isinstance(it, int) else ('ink', list(INK).index(it) + 1)
        d0 = scenario(b, *args, item_kind=item_kind, level=item_level)["per_day"]; d1 = scenario(b + 2, *args, item_kind=item_kind, level=item_level)["per_day"]
        help_rows.append((name, b, cost, d0, d1, d1 - d0 - cost))
    for name, l, b, price, mat, s0, s1 in vol_rows:
        m = l; cost = 5 if m - 2 <= 5 else 15
        help_rows.append((f"{name}, объём работы", b, cost, s0["per_day"], s1["per_day"], s1["per_day"] - s0["per_day"] - cost))

    return dict(vol_rows=vol_rows, help_rows=help_rows, rng_state=rng.getstate())


if __name__ == "__main__":
    build_tables()

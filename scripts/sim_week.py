"""Недельный бюджет Талиса (решение игрока 04.10.2026, по логам сессий 1–12): три варианта.
Сценарии: А — 12 ч (неделя с вылазками); Б — 22 ч (среднее); В — 30 ч (неделя в городе). Бдительный отдых — +8 к любому.
Пересчёт поверх sim.py и sim_player.py; правила не меняются."""

import random as _random
from rules_data import WEEK_PROF, WEEK_LAB

import sim_player as player

from sim_player import MB, NEED, BATCH, base_cost, growth_probs

from sim import HERB, P_SL, P_PRICE, CAT_PRICE, INSTAB, INK, check_success, roll, probs, scenario, p_bonus, potion_bonus

random = _random.Random(20261002)

WEEK = {"А": 12, "Б": 22, "В": 30}

DAYS = 12 / 8                                   # 1,5 рабочего дня

def prof(m): return WEEK_PROF[m]

def lab(m): return WEEK_LAB[m]

TALIS = {m: prof(m) + MB[m] + lab(m) for m in range(1, 11)}

ROOT_BONUS = prof(2) + MB[2] + 3

def ok_rate(b, sl, guidance=False):
    ok, un, fa = probs(b, sl)
    return ok + (1 - ok) * ok if guidance else ok

def growth_row(m, extra=0, guidance=False):
    b = TALIS[m] + extra
    ok, p5, p20 = growth_probs(b, P_SL[m], guidance)
    per = ok + p20                               # натуральная 20 — второй успех
    doses = NEED[m] / per
    hours = doses / BATCH.get(m, 1) * 2
    return b, doses, hours, doses * (base_cost(m) - p5 * m * HERB[m])   # на 5+ — экономия трав (7.7)

def ink_hour(m):
    """Доход в час на чернилах уровня m при бонусе Талиса на этом мастерстве (I–V; выше — как V)."""
    n = ["I", "II", "III", "IV", "V"][min(m, 5) - 1]
    price, herbs, ess, sl, cl, h = INK[n]
    return scenario(TALIS[m], sl, herbs + ess, price * .85, CAT_PRICE[cl], .5, h)["per_day"] / 8

def pot_hour(m):
    r = scenario(TALIS[m], P_SL[m], m * HERB[m], P_PRICE[m] * .85, CAT_PRICE[m], .5, 2)
    return r["per_try"] * BATCH.get(m, 1) / 2

def mc_ink(need, b, N=40000, *, rng=None):
    rng = random if rng is None else rng
    tot = 0
    for _ in range(N):
        p = a = 0
        while p < need:
            a += 1; p += rng.randint(1, 20) + b
        tot += a
    return tot / N

def mc_marks(need, b, sl, start=0, guidance=False, N=40000, *, rng=None):
    rng = random if rng is None else rng
    tot = 0
    for _ in range(N):
        m, a = start, 0
        while m < need:
            a += 1; d = rng.randint(1, 20)
            if guidance and d != 20 and (d == 1 or d + b < sl): d = rng.randint(1, 20)
            if d == 20: m += 3
            elif d == 1: pass
            elif d + b >= sl + 5: m += 2
            elif d + b >= sl: m += 1
        tot += a
    return tot / N

def silver_progress(d, b):
    """Прогресс этапа I по памятке мастера v0.2; половины не округляются."""
    total = d + b
    if d == 1:
        return 0
    if d == 20:
        return 2 * total
    if total >= 19:
        return total + 5
    if total >= 14:
        return total
    if total >= 10:
        return total / 2
    return 0

def silver_attempts(need, b, guidance=False):
    """Точное ожидание подходов до цели с учётом превышения прогресса.

    Только двухчасовые подходы: очистка, реагенты и дни восстановления
    не включены. Переброс одного провала, без ограничения пула очков.
    """
    weights = {}
    for first in range(1, 21):
        retry = guidance and first != 20 and (first == 1 or first + b < 14)
        outcomes = range(1, 21) if retry else (first,)
        for d in outcomes:
            progress = int(2 * silver_progress(d, b))
            weights[progress] = weights.get(progress, 0) + 1 / (20 * len(outcomes))
    # Состояния в половинах единицы: E(r) = 1 + p(0)E(r) + Σ p(k)E(max(0,r-k)).
    remaining = int(2 * need)
    expected = [0.0] * (remaining + 1)
    for r in range(1, remaining + 1):
        expected[r] = (1 + sum(p * expected[max(0, r - k)]
                              for k, p in weights.items() if k)) / (1 - weights.get(0, 0))
    return expected[remaining]

def p_open_in(hours, b=4, N=40000, *, rng=None):
    rng = random if rng is None else rng
    ok = 0
    for _ in range(N):
        m = t = 0
        while m < 3 and t < hours:
            t += 2; d = rng.randint(1, 20)
            if d == 20: m += 3
            elif d != 1 and d + b + 2 >= 17: m += 2
            elif d != 1 and d + b + 2 >= 12: m += 1
        while m >= 3 and t < hours:
            t += 2
            if rng.random() < ok_rate(b, 14): ok += 1; break
    return ok / N

NIGHT = 2 * HERB[2] + HERB[2]                   # доза на одну ночь: 2 травы II и эссенция Разум II — ≈1,5 зм


def build_tables(player_tables=None):
    """Continue the player stream; no calculations run during import."""
    if player_tables is None:
        player_tables = player.build_tables()
    rng = _random.Random()
    rng.setstate(player_tables["rng_state"])
    GROW = []

    for m in range(2, 10):
        b, doses, h, gold = growth_row(m)
        _, _, hg, _ = growth_row(m, guidance=True)
        lost = h * (ink_hour(m) - pot_hour(m))
        GROW.append((m, b, NEED[m], doses, h, hg, gold, lost))

    QUEUE = []

    for name, fn, h_per in [
        ("рецепт 2.2 по образцу (СЛ 10, +2 за образец, 1 отметка сразу)", lambda b, g: mc_marks(3, b + 2, 10, 1, g, rng=rng), 2),
        ("исследование чернил: осталось 70 из 100", lambda b, g: mc_ink(70, b, rng=rng), 2),
        ("рост мастерства 2 → 3: 15 успешных зелий 2.2", None, None),
        ("рецепт масел и мазей: 100 прогресса", lambda b, g: mc_ink(100, b, rng=rng), 2),
        ("обычная ступень формулы (СЛ 12, эссенция — подсказка +2) и первая варка", None, None),
        ("Корневая метка, этап I: осталось 16 из 30 (полная лаборатория, +6; подход — 2 часа)", lambda b, g: silver_attempts(16, ROOT_BONUS, g), 2),
    ]:
        row = []
        for extra, g in [(0, False), (0, True), (2, False)]:
            b = 4 + extra
            if name.startswith("рост"):
                ok, _, p20 = growth_probs(b, 10, g)
                per = ok + p20
                h = 15 / per / 2 * 2
            elif name.startswith("обычная"):
                h = mc_marks(3, b + 2, 12, 0, g, rng=rng) * 2 + 2 / ok_rate(b, 14, g)
            else:
                h = fn(b, g) * h_per
            row.append(h)
        QUEUE.append((name, row))

    OPEN_H = QUEUE[4][1][0]

    P_WEEK = p_open_in(12, rng=rng)

    QTOT_A = sum(r[1][0] for r in QUEUE)

    LONG = []

    for name, hrs in [("VI–VII (≈10 ч)", 10), ("VIII–IX (≈25 ч)", 25)]:
        for per_week in (12, 6, 4):
            weeks = -(-hrs // per_week)
            harsh = "испорчена" if weeks - 1 >= 4 else str(max(0, weeks - 2))
            LONG.append((name, per_week, weeks, "0", harsh))

    CH_OK = ok_rate(4, 12)

    P22_OK = ok_rate(4, 10)

    SUPPLY = [("только заряды и склянки I–II", 6 * CH_OK, 0), ("только зелья 2.2 партиями по 2", 0, 6 * 2 * P22_OK),
              ("пополам", 3 * CH_OK, 3 * 2 * P22_OK)]

    return dict(GROW=GROW, QUEUE=QUEUE, OPEN_H=OPEN_H, P_WEEK=P_WEEK, NIGHT=NIGHT,
                QTOT_A=QTOT_A, LONG=LONG, SUPPLY=SUPPLY, rng_state=rng.getstate())


if __name__ == "__main__":
    tables = build_tables()
    for row in tables["GROW"]:
        print(row)
    for row in tables["QUEUE"]:
        print(row)
    print(tables["OPEN_H"], tables["P_WEEK"], NIGHT, tables["QTOT_A"])
    print(tables["LONG"])
    print(tables["SUPPLY"])

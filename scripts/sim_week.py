"""Недельный бюджет Талиса (решение игрока 04.10.2026, по логам сессий 1–12): три варианта.
Сценарии: А — 12 ч (неделя с вылазками); Б — 22 ч (среднее); В — 30 ч (неделя в городе). Бдительный отдых — +8 к любому.
Пересчёт поверх sim.py и sim_player.py; правила не меняются."""
import random, sys
sys.argv = ["x", "10"]
exec(open(__file__.replace("sim_week.py", "sim.py"), encoding="utf-8").read().split("# проверка точного расчёта")[0])
_p = {"__file__": __file__.replace("sim_week.py", "sim_player.py")}
exec(open(_p["__file__"], encoding="utf-8").read(), _p)

WEEK = {"А": 12, "Б": 22, "В": 30}
DAYS = 12 / 8                                   # 1,5 рабочего дня

# Реальный бонус Талиса по мастерству: Инт +0; владение +2 сейчас, +3 с 5 уровня персонажа
# (≈7 квестов — раньше, чем мастерство 3); рабочее место +1 до мастерства 5,
# дальше нужна полная лаборатория (+3; потолок зелий 8) и мастерская (+5) для 9–10.
MB, NEED, BATCH, base_cost = _p["MB"], _p["NEED"], _p["BATCH"], _p["base_cost"]
def prof(m): return 2 if m <= 2 else 3 if m <= 7 else 4
def lab(m): return 1 if m <= 5 else 3 if m <= 8 else 5
TALIS = {m: prof(m) + MB[m] + lab(m) for m in range(1, 11)}

def ok_rate(b, sl, guidance=False):
    ok, un, fa = probs(b, sl)
    return ok + (1 - ok) * ok if guidance else ok

def growth_row(m, extra=0, guidance=False):
    b = TALIS[m] + extra
    per = ok_rate(b, P_SL[m], guidance) + 0.05      # натуральная 20 — второй успех
    doses = NEED[m] / per
    hours = doses / BATCH.get(m, 1) * 2
    return b, doses, hours, doses * base_cost(m)

def ink_hour(m):
    """Доход в час на чернилах уровня m при бонусе Талиса на этом мастерстве (I–V; выше — как V)."""
    n = ["I", "II", "III", "IV", "V"][min(m, 5) - 1]
    price, herbs, ess, sl, cl, h = INK[n]
    return scenario(TALIS[m], sl, herbs + ess, price * .85, CAT_PRICE[cl], .5, h)["per_day"] / 8

def pot_hour(m):
    r = scenario(TALIS[m], P_SL[m], m * HERB[m], P_PRICE[m] * .85, CAT_PRICE[m], .5, 2)
    return r["per_try"] * BATCH.get(m, 1) / 2

GROW = []
for m in range(2, 10):
    b, doses, h, gold = growth_row(m)
    _, _, hg, _ = growth_row(m, guidance=True)
    lost = h * (ink_hour(m) - pot_hour(m))
    GROW.append((m, b, NEED[m], doses, h, hg, gold, lost))

# Очередь исследований (сейчас, бонус +4; с помощником +6; «Волшебное указание» — переброс проваленной проверки)
def mc_ink(need, b, N=40000):
    tot = 0
    for _ in range(N):
        p = a = 0
        while p < need:
            a += 1; p += random.randint(1, 20) + b
        tot += a
    return tot / N

def mc_marks(need, b, sl, start=0, guidance=False, N=40000):
    tot = 0
    for _ in range(N):
        m, a = start, 0
        while m < need:
            a += 1; d = random.randint(1, 20)
            if guidance and d != 20 and (d == 1 or d + b < sl): d = random.randint(1, 20)
            if d == 20: m += 3
            elif d == 1: pass
            elif d + b >= sl + 5: m += 2
            elif d + b >= sl: m += 1
        tot += a
    return tot / N

def mc_silver(need, b, guidance=False, N=40000):
    tot = 0
    for _ in range(N):
        p = a = 0
        while p < need:
            a += 1; d = random.randint(1, 20)
            if guidance and d != 20 and (d == 1 or d + b < 14): d = random.randint(1, 20)
            if d == 1: continue
            if d + b >= 14: p += 2 * (d + b) if d == 20 else d + b
        tot += a
    return tot / N

QUEUE = []
for name, fn, h_per in [
    ("рецепт 2.2 по образцу (СЛ 10, +2 за образец, 1 отметка сразу)", lambda b, g: mc_marks(3, b + 2, 10, 1, g), 2),
    ("исследование чернил: осталось 70 из 100", lambda b, g: mc_ink(70, b), 2),
    ("рост мастерства 2 → 3: 15 успешных зелий 2.2", None, None),
    ("рецепт масел и мазей: 100 прогресса", lambda b, g: mc_ink(100, b), 2),
    ("обычная ступень формулы (СЛ 12, эссенция — подсказка +2) и первая варка", None, None),
    ("серебрянка, этап 1: осталось 16 из 30 (попытка — 2 часа, допущение)", lambda b, g: mc_silver(16, b, g), 2),
]:
    row = []
    for extra, g in [(0, False), (0, True), (2, False)]:
        b = 4 + extra
        if name.startswith("рост"):
            per = ok_rate(b, 10, g) + 0.05
            h = 15 / per / 2 * 2
        elif name.startswith("обычная"):
            h = mc_marks(3, b + 2, 12, 0, g) * 2 + 2 / ok_rate(b, 14, g)
        else:
            h = fn(b, g) * h_per
        row.append(h)
    QUEUE.append((name, row))

# Бдительный отдых: открыть обычную ступень «Эликсира Разума» и сварить первую партию
OPEN_H = QUEUE[4][1][0]
def p_open_in(hours, b=4, N=40000):
    ok = 0
    for _ in range(N):
        m = t = 0
        while m < 3 and t < hours:
            t += 2; d = random.randint(1, 20)
            if d == 20: m += 3
            elif d != 1 and d + b + 2 >= 17: m += 2
            elif d != 1 and d + b + 2 >= 12: m += 1
        while m >= 3 and t < hours:
            t += 2
            if random.random() < ok_rate(b, 14): ok += 1; break
    return ok / N
P_WEEK = p_open_in(12)
NIGHT = 2 * HERB[2] + HERB[2]                   # доза на одну ночь: 2 травы II и эссенция Разум II — ≈1,5 зм
QTOT_A = sum(r[1][0] for r in QUEUE)

# Долгая варка и перерыв (6.3): неделя без подходов — простой; первая неделя простоя бесплатна,
# каждая следующая подряд — +1 дефект, через месяц простоя варка испорчена.
# Чтение 1: неделя с хотя бы одним подходом — не простой. Чтение 2 (жёсткое): простоем считается
# каждая неделя после первой, пока варка не закончена.
LONG = []
for name, hrs in [("VI–VII (≈10 ч)", 10), ("VIII–IX (≈25 ч)", 25)]:
    for per_week in (12, 6, 4):
        weeks = -(-hrs // per_week)
        harsh = "испорчена" if weeks - 1 >= 4 else str(max(0, weeks - 2))
        LONG.append((name, per_week, weeks, "0", harsh))

# Поставщик группы за неделю (12 ч, бонус +4): заряды и склянки I–II (СЛ 12) и партии зелий 2.2
CH_OK = ok_rate(4, 12)
P22_OK = ok_rate(4, 10)
SUPPLY = [("только заряды и склянки I–II", 6 * CH_OK, 0), ("только зелья 2.2 партиями по 2", 0, 6 * 2 * P22_OK),
          ("пополам", 3 * CH_OK, 3 * 2 * P22_OK)]

if __name__ == "__main__":
    for r in GROW: print(r)
    for q in QUEUE: print(q)
    print(OPEN_H, P_WEEK, NIGHT, QTOT_A); print(LONG); print(SUPPLY)

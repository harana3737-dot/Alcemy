"""Долгая варка VI+ объёмом работы (правила, 6.3) и помощник (6.4). Монте-Карло.
Подход 2 часа: успех — +итог; 5+ — +итог и метка; 10+ — +итог и 2 метки; провал 1–4 — +½ итога и заминка
(3 заминки = дефект); провал 5+ — 0 и дефект; нат. 20 — прогресс ×2 и метка; нат. 1 — 0, −d20, дефект.
Завершение — проверка с модификатором (метки − дефекты), от −2 до +2. Помощник: +2 к прогрессу подхода
и +2 к завершающей проверке."""
import random, sys
sys.argv = ["x", "10"]
exec(open(__file__.replace("sim_volume.py", "sim.py"), encoding="utf-8").read().split("# проверка точного расчёта")[0])
random.seed(90)

VOL = {6: 90, 7: 90, 8: 240}
SL_E = {6: 19, 7: 21, 8: 23}            # СЛ эликсира / чернил того же уровня
ESS = {6: HERB[6], 7: 2.5 * HERB[7], 8: 2.5 * HERB[8]}   # VII–VIII — 2–3 травы, середина
CAT_E = {6: 350, 7: 350, 8: 1750}


def volume_run(bonus, sl, vol, helper):
    prog = marks = hitch = defects = n = 0
    while prog < vol:
        n += 1
        d = random.randint(1, 20); t = d + bonus
        if d == 20:
            prog += 2 * t; marks += 1
        elif d == 1:
            prog = max(0, prog - random.randint(1, 20)); defects += 1
        elif t >= sl:
            prog += t; marks += 2 if t - sl >= 10 else 1 if t - sl >= 5 else 0
        elif sl - t <= 4:
            prog += t / 2; hitch += 1
            if hitch == 3:
                hitch = 0; defects += 1
        else:
            defects += 1
        if helper and d != 1:
            prog += 2
        if n > 200:
            break
    mod = max(-2, min(2, marks - defects))
    return n, roll(bonus + mod + (2 if helper else 0), sl)


def volume_stats(bonus, lvl, price, mat, helper=False, runs=20000):
    sl, vol = SL_E[lvl], VOL[lvl]
    cat = CAT_E[lvl] / 5                  # пять стабильных применений, без риска
    A = P = OK = 0
    for _ in range(runs):
        n, r = volume_run(bonus, sl, vol, helper)
        A += n
        P += price * .85 if r == "ok" else price * .85 * .5 if r == "unst" else 0
        OK += r == "ok"
    apr = A / runs
    profit = P / runs - mat - cat
    return dict(approaches=apr, hours=apr * 2, ok=OK / runs, profit=profit, per_day=profit / (apr * 2 / 8))


def typ(l):
    MB = {1: 0, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 7: 3, 8: 4, 9: 4, 10: 5}
    LAB = {1: 0, 2: 0, 3: 0, 4: 1, 5: 1, 6: 3, 7: 3, 8: 3, 9: 5, 10: 5}
    return 7 + MB[l] + LAB[l]


# заряды и склянки = чернила того же уровня: цена набора, травы 1/3, эссенция уровня
CHG = {6: 7500, 7: 12500, 8: 25000}
EFF = {6: ("Невидимость", 250), 7: ("Полёт", 500), 8: ("Скорость", 1750)}
vol_rows = []
ROMN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
for l in (6, 7, 8):
    b = typ(l)
    items = [(f"заряд, склянка или чернила {ROMN[l]}", CHG[l], CHG[l] / 3 + ESS[l]),
             (f"эликсир-эффект {ROMN[l]} ({EFF[l][0]})", EFF[l][1], l * HERB[l] + ESS[l])]
    for name, price, mat in items:
        s0 = volume_stats(b, l, price, mat, False)
        s1 = volume_stats(b, l, price, mat, True)
        vol_rows.append((name, l, b, price, mat, s0, s1))

# помощник на обычных варках: +2 к проверке, цена по мастерству помощника (не ниже мастерства − 2)
help_rows = []
cases = [("Талис сейчас: зелье 2.2", 4, 2, 2), ("Талис сейчас: чернила I", 4, 2, "I"), ("Талис сейчас: чернила II", 4, 2, "II"),
         ("зелье 4.4, типичный бонус", typ(4), 4, 4), ("зелье 5.5, типичный бонус", typ(5), 5, 5),
         ("чернила IV, бонус +8", 8, 4, "IV"), ("чернила V, бонус +8", 8, 5, "V")]
for name, b, mast, it in cases:
    cost = 2 if mast - 2 <= 2 else 5 if mast - 2 <= 5 else 15
    if isinstance(it, int):
        l = it; args = (P_SL[l], l * HERB[l], P_PRICE[l] * .85, CAT_PRICE[l], .5, 2)
    else:
        price, herbs, ess, sl, cl, h = INK[it]; args = (sl, herbs + ess, price * .85, CAT_PRICE[cl], .5, h)
    d0 = scenario(b, *args)["per_day"]; d1 = scenario(b + 2, *args)["per_day"]
    help_rows.append((name, b, cost, d0, d1, d1 - d0 - cost))
for name, l, b, price, mat, s0, s1 in vol_rows:
    m = l; cost = 5 if m - 2 <= 5 else 15
    help_rows.append((f"{name}, объём работы", b, cost, s0["per_day"], s1["per_day"], s1["per_day"] - s0["per_day"] - cost))

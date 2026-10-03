"""Расчёты для игрока поверх sim.py: лечение на золото, риск катализатора, самодельный катализатор,
чернила против покупки у Марты, стоимость прокачки мастерства 1 → 10. Правила v0.3.
«Родной» бонус: Инт +0 (как у Талиса), владение по брекетам, мастерство алхимика, минимальная лаборатория."""
import random, sys
sys.argv = ["x", "10"]
exec(open(__file__.replace("sim_player.py", "sim.py"), encoding="utf-8").read().split("# проверка точного расчёта")[0])

PROF = {1: 2, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3, 7: 3, 8: 4, 9: 4, 10: 4}
MB = {1: 0, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 7: 3, 8: 4, 9: 4, 10: 5}
LAB = {1: 0, 2: 0, 3: 0, 4: 1, 5: 1, 6: 3, 7: 3, 8: 3, 9: 5, 10: 5}
NATIVE = {l: PROF[l] + MB[l] + LAB[l] for l in range(1, 11)}   # Инт +0
HEAL = {1: (2.5, 2.5), 2: (6, 6), 3: (9, 9), 4: (6, 9.5), 5: (8, 12.5), 6: (12.5, 27), 7: (17.5, 36), 8: (22, 61), 9: (25, 64), 10: (39, 136.5)}
BATCH = {1: 2, 2: 2, 3: 4, 4: 4, 5: 4}     # партия зелья своего уровня на мастерстве = уровню (6.2); 6.6+ — без партий
NEED = {1: 10, 2: 15, 3: 20, 4: 25, 5: 25, 6: 25, 7: 25, 8: 25, 9: 25}   # успехов зелья уровня m для перехода m → m+1


def base_cost(l):
    return l * HERB[l] + CAT_PRICE[l] / 5


# 1. лечение на золото
heal_rows = [(l, HEAL[l][0], HEAL[l][1], base_cost(l)) for l in range(1, 11)]

# 2. риск нестабильности по применениям при родном бонусе
def instab(b, use):
    return max(0.05, min(1, (INSTAB[use - 6] - b - 1) / 20))
instab_rows = [(l, NATIVE[l], [instab(NATIVE[l], u) for u in range(6, 11)]) for l in (3, 4, 6, 8, 9, 10)]

# 3. самодельный катализатор (5.3): СЛ I 11, II 17, III 21, IV 25; провал 1–4 — 3 стабильных применения
CAT_ROWS = []
for order, (sl, lvl, price) in {"I": (11, 3, 70), "II": (17, 6, 350), "III": (21, 8, 1750), "IV": (25, 10, 7500)}.items():
    b = NATIVE[lvl]
    ok, un, fa = probs(b, sl)
    value = ok * price + un * price * 3 / 5
    CAT_ROWS.append((order, price, sl, b, ok, un, fa, value, price / 2))

# 4. чернила для себя против покупки у Марты (продажная цена набора)
INK_SELF = []
for n, ml in [("I", 1), ("II", 2), ("III", 3), ("IV", 4), ("V", 5)]:
    price, herbs, ess, sl, cl, h = INK[n]
    b = NATIVE[ml]
    ok, un, fa = probs(b, sl)
    cost = (herbs + ess + CAT_PRICE[cl] / 5) / (1 - fa)      # нестабильные чернила годятся (−2 к Начертанию)
    INK_SELF.append((n, b, sl, fa, cost, price))
_v = {"__file__": __file__.replace("sim_player.py", "sim_volume.py")}
exec(open(_v["__file__"], encoding="utf-8").read(), _v)
for l, n in [(6, "VI"), (7, "VII"), (8, "VIII")]:
    price = _v["CHG"][l]; mat = price / 3 + _v["ESS"][l]
    st = _v["volume_stats"](NATIVE[l], l, price, mat, False, 10000)
    ok_u = st["ok"]          # доля годных (успех); нестабильные тоже годятся, но здесь консервативно
    cost = (mat + _v["CAT_E"][l] / 5) / max(ok_u, 1e-9)
    INK_SELF.append((n, NATIVE[l], _v["SL_E"][l], 1 - ok_u, cost, price))

# 5. прокачка мастерства 1 → 10 (только зелья своего уровня)
def growth(extra=0, guidance=False):
    rows = []
    for m in range(1, 10):
        b = NATIVE[m] + extra
        ok, un, fa = probs(b, P_SL[m])
        if guidance:                     # переброс любого провала; пул не ограничен — нижняя граница
            ok = ok + (1 - ok) * ok
        per_dose = ok + 0.05             # натуральная 20 — второй успех
        doses = NEED[m] / per_dose
        batch = BATCH.get(m, 1)
        hours = doses / batch * 2
        gold = doses * base_cost(m)
        rows.append((m, NEED[m], ok, doses, batch, hours, gold))
    return rows

GROWTH = {"базовый": growth(), "с помощником (+2)": growth(2), "с «Волшебным указанием»": growth(0, True),
          "с повязкой интеллекта (+4)": growth(4), "повязка + указание": growth(4, True)}

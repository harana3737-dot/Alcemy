"""Расчёты для игрока поверх sim.py: лечение на золото, риск катализатора, самодельный катализатор,
чернила против покупки у Анариэль, стоимость прокачки мастерства 1 → 10. Правила v0.3.
«Родной» бонус: Инт +0 (как у Талиса), владение по брекетам, мастерство алхимика, минимальная лаборатория."""

from rules_data import CAT_STABLE, PLAYER_PROF, MB, PLAYER_LAB, HEAL, OWN_BATCH, NEED, CAT_DC, CAT_ORDER_PRICE, ROM

import random as _random

import sim_volume as volume

from sim import HERB, P_SL, P_PRICE, CAT_PRICE, INSTAB, INK, check_success, roll, probs, scenario, p_bonus, potion_bonus

PROF = PLAYER_PROF


LAB = PLAYER_LAB

NATIVE = {l: PROF[l] + MB[l] + LAB[l] for l in range(1, 11)}   # Инт +0


BATCH = OWN_BATCH


def base_cost(l):
    return l * HERB[l] + CAT_PRICE[l] / CAT_STABLE

def instab(b, use):
    return 1 - probs(b, INSTAB[use - CAT_STABLE - 1])[0]

def growth_probs(b, sl, guidance=False):
    """Успех, экономия трав на 5+ и нат. 20 после не более одного переброса провала.

    Пул очков не ограничен. Нат. 20 даёт вторую единицу роста, поэтому
    её вероятность возвращается отдельно от вероятности успеха.
    """
    ok, _, _ = probs(b, sl)
    p5, p20 = p_bonus(b, sl)
    factor = 1 + (1 - ok) if guidance else 1
    return ok * factor, p5 * factor, p20 * factor

def growth(extra=0, guidance=False):
    rows = []
    for m in range(1, 10):
        b = NATIVE[m] + extra
        ok, p5, p20 = growth_probs(b, P_SL[m], guidance)
        per_dose = ok + p20              # натуральная 20 — второй успех
        doses = NEED[m] / per_dose
        batch = BATCH.get(m, 1)
        hours = doses / batch * 2
        gold = doses * (base_cost(m) - p5 * m * HERB[m])   # на 5+ — экономия трав (7.7)
        rows.append((m, NEED[m], ok, doses, batch, hours, gold))
    return rows

def _ink2_day(b):
    price, herbs, ess, sl, cl, h = INK["II"]
    return scenario(b, sl, herbs + ess, price * .85, CAT_PRICE[cl], .5, h, item_kind='ink', level=2)["per_day"]


def build_tables(volume_tables=None):
    """Continue the reference volume stream without rebuilding its tables."""
    if volume_tables is None:
        volume_tables = volume.build_tables()
    rng = _random.Random()
    rng.setstate(volume_tables["rng_state"])
    heal_rows = [(l, HEAL[l][0], HEAL[l][1], base_cost(l)) for l in range(1, 11)]

    instab_rows = [(l, NATIVE[l], [instab(NATIVE[l], u) for u in range(6, 11)]) for l in (3, 4, 6, 8, 9, 10)]

    CAT_ROWS = []

    for order, (sl, lvl, price) in {ROM[o]: (CAT_DC[o], l, CAT_ORDER_PRICE[o]) for o, l in enumerate((3, 6, 8, 10), 1)}.items():
        b = NATIVE[lvl]
        ok, un, fa = probs(b, sl)
        # 5.3: нат. 20 — 7 стабильных, 5+ — 6, успех — 5, провал 1–4 — 4; ценность ∝ стабильным применениям (5 = цена)
        n20 = 0.05; hi = sum(1 for d in range(2, 20) if d + b >= sl + 5) / 20
        value = price * ((ok - hi - n20) * CAT_STABLE + hi * (CAT_STABLE + 1) + n20 * (CAT_STABLE + 2) + un * (CAT_STABLE - 1)) / CAT_STABLE
        CAT_ROWS.append((order, price, sl, b, ok, un, fa, value, price / 2))

    INK_SELF = []

    for n, ml in [("I", 1), ("II", 2), ("III", 3), ("IV", 4), ("V", 5)]:
        price, herbs, ess, sl, cl, h = INK[n]
        b = NATIVE[ml]
        ok, un, fa = probs(b, sl)
        cost = (herbs + ess + CAT_PRICE[cl] / CAT_STABLE) / (1 - fa)      # нестабильные чернила годятся (−2 к Начертанию)
        INK_SELF.append((n, b, sl, fa, cost, price))

    for l, n in [(6, "VI"), (7, "VII"), (8, "VIII")]:
        price = volume.CHG[l]; mat = price / 3 + volume.ESS[l]
        st = volume.volume_stats(NATIVE[l], l, price, mat, False, 10000, rng=rng)
        ok_u = st["ok"]          # доля годных (успех); нестабильные тоже годятся, но здесь консервативно
        cost = (mat + volume.CAT_E[l] / CAT_STABLE) / max(ok_u, 1e-9)
        INK_SELF.append((n, NATIVE[l], volume.SL_E[l], 1 - ok_u, cost, price))

    GROWTH = {"базовый": growth(), "с помощником (+2)": growth(2), "с «Волшебным указанием»": growth(0, True),
              "с тиарой интеллекта +2 (+1)": growth(1), "тиара + указание": growth(1, True)}

    _g0 = growth()

    ITEMS_ALCH = []

    for name, rar, extra, price, buy in [("Тиара интеллекта +2", "Инт 10 → 12, настройка", 1, 500, "500"),
                                         ("Камень удачи", "необычный, настройка", 1, 350, "≈350 (100–600)"),
                                         ("Тиара +2 и камень удачи", "две настройки", 2, 850, "≈850"),
                                         ("Тиара интеллекта +4", "Инт 10 → 14, настройка", 2, None, "цена — уточнить"),
                                         ("Камень Йоун «Интеллект»", "очень редкий, настройка", 1, None, "купить почти невозможно"),
                                         ("Фолиант ясной мысли", "очень редкий, навсегда", 1, None, "купить почти невозможно"),
                                         ("Камень Йоун «Мастерство»", "легендарный, настройка", 1, None, "только сюжетно")]:
        gain = _ink2_day(4 + extra) - _ink2_day(4)
        g = growth(extra)
        ITEMS_ALCH.append((name, rar, extra, buy, gain, price / gain if price else None,
                           sum(r[6] for r in _g0) - sum(r[6] for r in g), sum(r[5] for r in _g0) - sum(r[5] for r in g)))

    return dict(heal_rows=heal_rows, instab_rows=instab_rows, CAT_ROWS=CAT_ROWS,
                INK_SELF=INK_SELF, GROWTH=GROWTH, ITEMS_ALCH=ITEMS_ALCH,
                rng_state=rng.getstate(), scenario=scenario)


if __name__ == "__main__":
    print({key: value for key, value in build_tables().items()
           if key not in ("rng_state", "scenario")})

"""Сверка карточек с таблицами правил v0.3. Запуск: python3 scripts/cards/check.py
Ошибки — расхождение с правилом; предупреждения — то, что стоит проверить глазами."""
import pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
from cards_model import (
    HERE,
    RAR,
    ROM,
    ROOT,
    prepare_cards,
)
def main():
    C = prepare_cards()

    TOX = {"обычный": 1, "необычный": 2, "редкий": 3, "очень редкий": 4, "легендарный": 5}
    CORR = {"обычный": (10, 25), "необычный": (30, 100), "редкий": (150, 500), "очень редкий": (1000, 2500), "легендарный": (5000, 25000)}
    INK = {1: 30, 2: 120, 3: 300, 4: 1200, 5: 2500, 6: 7500, 7: 12500, 8: 25000}
    MOVE_OK = {"Поспешное отступление", "Кинетический рывок", "Левитация"}   # передвижение — вне 8.9 по правилу (Левитация — Ж-107)
    PRICE_BY_SPELL_EXC = {"Молниевый выдох", "Склянка стихии: большая"}   # уровень поднят за урон, цена по заклинанию (8.8)

    err, warn = [], []
    E = lambda c, m: err.append(f"{c['name']} ({ROM[c['lvl']]}): {m}")
    W = lambda c, m: warn.append(f"{c['name']} ({ROM[c['lvl']]}): {m}")


    def num(p):
        p = p.replace(" ", "").replace("≈", "").split("усл")[0].replace("+", "")
        return int(re.sub(r"[^0-9]", "", p) or 0)


    for c in C:
        l, k, rar = c["lvl"], c["cls"], RAR[c["lvl"]]
        # эссенция того же уровня
        m = re.search(r"\b(I|II|III|IV|V|VI|VII|VIII|IX|X)\b", c["ess"])
        if m and not c["ess"].startswith("по ") and m.group(1) != ROM[l]:
            E(c, f"эссенция {c['ess']} не того уровня")
        # токсичность
        t = c["tox"].split(" ")[0].rstrip(";")
        if k == "psn":
            pass  # токсичность только у выпившего — проверяется по базовому заряду
        elif k in ("fl", "oils", "oilw", "salve"):
            if not t.startswith("0"):
                E(c, f"токсичность {t}, а склянки, масла и мази её не дают")
        elif t.isdigit() and int(t) not in (0, TOX[rar]):
            E(c, f"токсичность {t}, по редкости «{rar}» должна быть {TOX[rar]} (или 0 у мягких)")
        elif t == "0" and "мягк" not in c["tox"]:
            W(c, "токсичность 0 без пометки «мягкий»")
        # цена
        p = num(c["price"])
        if k in ("chg", "psn", "rea", "fl", "oils"):
            sm = re.search(r"(\d) ур\.", c["src_raw"])
            if sm:
                exp = INK[int(sm.group(1))]
                if p != exp:
                    E(c, f"цена {c['price']}, по модели чернил для заклинания {sm.group(1)} уровня — {exp}")
                elif int(sm.group(1)) != l and c["name"] not in PRICE_BY_SPELL_EXC and k != "oils":
                    W(c, f"уровень эликсира {ROM[l]} не равен уровню заклинания {sm.group(1)}")
            else:
                W(c, "не найден уровень исходного заклинания для проверки цены")
        else:
            lo, hi = CORR[rar]
            extra = re.search(r"пыль|компонент|жемчуж", (c["note"] or "") + (c["mech"] or ""))
            if p < lo or (p > hi and not extra):
                E(c, f"цена {c['price']} вне коридора «{rar}» {lo}–{hi}")
        # концентрация у зарядов и склянок
        if k in ("chg", "rea", "fl", "oils") and "концентрация" in c["src_raw"] and (c["conc"] or "нет").startswith("нет") and "мгновенный" not in (c["conc"] or ""):
            E(c, "исходное заклинание с концентрацией, а в карточке её нет")
        # алхимическая концентрация у эффектов
        if k == "eff" and "концентрация" in c["src_raw"] and c["a89"].startswith("нет") and "0" != t and c["name"] not in MOVE_OK:
            W(c, "эффект из концентрационного заклинания не под алх. концентрацией — проверить, что это передвижение или утилита")
        if not c.get("dur"):
            E(c, "нет длительности")

    # уровни официальных — против таблицы А.2 правил
    rules = open(ROOT / "Алхимия Талиса — правила v0.3 (черновик на утверждение).md", encoding="utf-8").read()
    a2 = rules[rules.index("## А.2 Пересмотр"):rules.index("## А.3")]
    by = {c["name"]: c for c in C}
    for row in re.findall(r"^\| ([^|]+?) \| [^|]+ \| ([^|]+?) \|", a2, re.M):
        name, lv = row
        if name in by:
            want = re.match(r"(I|II|III|IV|V|VI|VII|VIII|IX|X)\b", lv)
            if want and want.group(1) != ROM[by[name]["lvl"]]:
                E(by[name], f"в А.2 правил уровень {want.group(1)}, в карточке {ROM[by[name]['lvl']]}")

    print(f"Карточек: {len(C)}. Ошибок: {len(err)}. Предупреждений: {len(warn)}.")
    for x in err:
        print("ОШИБКА  ", x)
    for x in warn:
        print("проверить", x)
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()

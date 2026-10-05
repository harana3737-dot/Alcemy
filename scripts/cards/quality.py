"""Рекомендуемые бонусы качества (7.7, 8.12) по каждой карточке — документ игрока, не для карточек мастера.
Запуск: python3 scripts/cards/quality.py → «Бонусы качества по карточкам.md»."""
import pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
_g = {"__file__": str(HERE / "gen.py")}
exec(open(HERE / "gen.py", encoding="utf-8").read().split("TR = dict(zip(")[0], _g)
globals().update({k: _g[k] for k in ("C", "ROM", "CLS", "CLS_ORDER", "saves", "area", "ROOT")})


exec(open(HERE / "upcast.py", encoding="utf-8").read())
POURED = {"Эликсир правды", "Любовный напиток"}


def quality(c):
    """Рекомендуемый бонус качества (8.12) для себя; на продажу — экономия трав и ещё одна доза."""
    k, eff, dur, up = c["cls"], c["eff"], c["dur"], UPCAST.get(c["name"], "none")
    dice = "dice" in up
    has_save = saves(c) not in ("нет", "")
    if k == "psn":
        return "Сильная привязка (+1 к СЛ: у яда она всегда табличная)", "Крепкая привязка (+2 к СЛ)"
    if k in ("chg", "rea"):
        b5 = "Усиленное заклинание (+кубы, как ячейкой выше)" if dice else ("Долгое окно (4 часа); союзнику — Сильная привязка" if has_save else "Долгое окно (4 часа)")
        b20 = "Полное усиление (+1 цель)" if "targets" in up else "Полное усиление (длиннее эффект)" if "duration" in up else "Двойной заряд"
        return b5, b20
    if k == "fl":
        dmg = "Урон" in c["tasks"]
        ar = area(c) or ""
        if dmg:
            big = bool(re.search(r"(1[0-9]|[2-9][0-9]) фт", ar))
            lng = "Затяжная склянка (повтор половины кубов в следующий ход)" if dur.startswith("мгновенно") else "Затяжная склянка (длительность ×2)"
            return ("Щадящая (союзники в области проходят спасбросок — половина урона)" if big else "Ровный взрыв (переброс единиц)"), lng
        if has_save:
            return "Сильная привязка (+1 к СЛ)", "Широкая склянка (+5 фт области)"
        return "Дальний бросок (60 фт)", "Затяжная склянка (длительность ×2)"
    if k == "oils":
        return ("Сильная привязка (+1 к СЛ)" if has_save else "Долгое масло (держится на оружии 2 часа)"), "Двойная кара"
    if k == "oilw":
        return "Быстрое нанесение (бонусным действием)", ("Усиленное масло (+кубик урона)" if re.search(r"\d+к\d+", eff) else "Ещё одна доза")
    if k == "salve":
        return "Долгое масло (длительность ×2)", "Ещё одна доза"
    # эликсир-эффект
    if c["name"] in POURED:
        return "Незаметное (подлить в еду или питьё)", "Ещё одна доза"
    if dur.startswith("мгновенно"):
        return "Лёгкий глоток (влить союзнику бонусным действием)", "Ещё одна доза"
    tox = c["tox"].split(" ")[0]
    short = bool(re.match(r"(1 минута|10 минут|до )", dur))
    if tox not in ("0", "0;") and short:
        return "Чистый (токсичность дозы уходит за 10 минут)", "Ещё одна доза"
    if re.search(r"час|сутки", dur):
        return "Долгое действие (×1,5, не больше +1 часа)", "Двойной срок (×2, не больше +8 часов)"
    return "Долгое действие (×1,5, не больше +1 часа)", "Ещё одна доза"


cards = sorted(C, key=lambda c: (c["lvl"], CLS_ORDER.index(c["cls"]), c["name"]))
L = ["# Бонусы качества по карточкам\n",
     "Документ игрока: какой бонус брать на успехе 5+ и натуральной 20 для каждого рецепта из каталога, если варишь для себя. "
     "На продажу — всегда экономия трав на 5+ и ещё одна доза на 20. Логика выбора — в «Бонусы за 5+ и 20 — что выгоднее брать». "
     "У контрольных ядов своего списка бонусов в 8.12 нет; взят список зарядов (предложение).\n"]
for k in CLS_ORDER:
    items = [c for c in cards if c["cls"] == k]
    if not items:
        continue
    L.append(f"## {CLS[k].capitalize()} ({len(items)})\n")
    L.append("| Рецепт | Ур. | На 5+ | На 20 |\n| --- | --- | --- | --- |")
    for c in items:
        b5, b20 = quality(c)
        L.append(f"| {c['name']} | {ROM[c['lvl']]} | {b5} | {b20} |")
    L.append("")
(ROOT / "Бонусы качества по карточкам.md").write_text("\n".join(L), encoding="utf-8")
print("ok", len(cards))

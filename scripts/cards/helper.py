"""Помощник варки — интерактивная страница игрока: рецепт + ситуация → бонус 5+ и 20, СЛ, партия, шансы;
вкладка «Пояс» — сумка, выпитое, токсичность (8.7), алхимическая концентрация (8.9), отдых.
Не для карточек мастера. Запуск: python3 scripts/cards/helper.py → «Помощник варки.html»."""
import hashlib, json, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
_g = {"__file__": str(HERE / "quality.py")}
exec(open(HERE / "quality.py", encoding="utf-8").read().split("\n\ncards = sorted")[0], _g)
C, CLS, CLS_ORDER, ROOT = _g["C"], _g["CLS"], _g["CLS_ORDER"], _g["ROOT"]

data = []
for c in sorted(C, key=lambda c: (c["lvl"], CLS_ORDER.index(c["cls"]), c["name"])):
    b5, b20 = _g["quality"](c)
    data.append(dict(n=c["name"], l=c["lvl"], k=c["cls"], f=c["fam"] or "", e=c["ess"], t=c["tox"], d=c["dur"],
                     p=c["price"], b=c["base"], a=c["a89"].startswith("да"), s=_g["saves"](c), ar=_g["area"](c) or "", tk=c["tasks"],
                     up=_g["UPCAST"].get(c["name"], "none"), b5=b5, b20=b20, eff=c["eff"]))

# Сумка из листа персонажа: блоки «Зелья и расходники» и «На разборку»
CARD_OF = {"Зелье сопротивления (некротика)": "Сопротивление", "Зелье подводного дыхания": "Водное дыхание"}
sheet = (pathlib.Path(ROOT) / "Талис — лист персонажа.md").read_text(encoding="utf-8")
seed, block = [], None
for line in sheet.split("## Снаряжение", 1)[1].split("\n"):
    t = line.strip()
    if t in ("Зелья и расходники", "На разборку"):
        block = t
    elif t and not t.startswith("•"):
        block = None
    elif t and block:
        n = t.lstrip("• ").strip()
        m = re.search(r"\s*(?:×(\d+)|\((\d+) исп\.\))$", n)
        q = int(m.group(1) or m.group(2)) if m else 1
        n = n[:m.start()] if m else n
        it = dict(n=n, q=q, note="на разборку" if block == "На разборку" else "")
        if n in CARD_OF:
            it["card"] = CARD_OF[n]
        seed.append(it)
for it in seed:
    it["who"] = "p1"
# Союзники — по строке «Зелья союзников» в листе
ALLY = [dict(n="Зелье подводного дыхания", q=1, note="", card="Водное дыхание", who=w) for w in ("pF", "pL")]
seed += ALLY
# Материалы Талиса — по блоку «Ингредиенты» листа (сверено 05.10.2026)
MAT = dict(
    gold=132.58,  # «Монеты» в листе
    herbs=[dict(k="heal", l=1, q=5), dict(k="poison", l=1, q=4)],  # лечебные 1 ур. ×4 + «трава 1.1» ×1; ядовитые 1 ур. ×4 (5 от куа-тоа − 1 на опыт с водорослями; сверено 06.10)
    ess=[dict(id="e1", n="Костяная пыль", types=["Смерть/душа"], l=1, q=1, note=""),
         dict(id="e2", n="Хитин", types=["Чувства", "Тело"], l=1, q=1, note="одна эссенция: Чувства или Тело"),
         dict(id="e3", n="Соль алхимическая", types=["Вода/дыхание"], l=1, q=1, note="годится и как консервант"),
         dict(id="e4", n="Проба крови шахтёра", types=["Тело"], l=2, q=1, st="fresh", note="влажный трофей, законсервирован холодом до 7 дней; вторая у Лаэля")],
    cat=[],
    other=[dict(n="Сырой катализатор I порядка", q=1, note="сначала изготовить (5.3, СЛ 11)"),
           dict(n="Лечебные травы на 60 зм", q=1, note="материалы этапа I Корневой метки, не для варки"),
           dict(n="Ошмётки руды из аномалии", q=1, note="возможно, сырьё для катализатора — порядок у мастера")])
seed_id = hashlib.sha1(json.dumps(seed, ensure_ascii=False).encode()).hexdigest()[:10]

# Дорогие компоненты исходных заклинаний (8.10; по текстам 5etools): use — расходуемый (тратится при каждой варке), иначе инструмент рецепта
COMP = {
    "Опознание": ("жемчужина", "жемчужина не дешевле 100 зм", 100, False),
    "Предсказание": ("жетоны", "особые палочки, кости или жетоны на 25 зм", 25, False),
    "Необнаружимость": ("алмазная пыль", "алмазная пыль 25 зм", 25, True),
    "Ясновидение": ("фокус", "фокус на 100 зм: рог с самоцветами или стеклянный глаз", 100, False),
    "Высшее восстановление": ("алмазная пыль", "алмазная пыль 100 зм", 100, True),
    "Каменная кожа": ("алмазная пыль", "алмазная пыль 100 зм", 100, True),
    "Рассвет": ("подвеска", "подвеска-солнце на 100 зм", 100, False),
    "Истинное зрение": ("мазь для глаз", "мазь для глаз 25 зм (грибной порошок, шафран, жир)", 25, True),
    "Потусторонний облик": ("символ", "предмет с символом Внешних планов, 500 зм", 500, False),
    "Силовая клетка": ("рубиновая пыль", "рубиновая пыль 1 500 зм", 1500, True),
    "Священная аура": ("реликварий", "реликварий с реликвией, 1 000 зм", 1000, False),
    "Наблюдение": ("фокус", "фокус на 1 000 зм: хрустальный шар, серебряное зеркало или купель", 1000, False),
    "Связь сущностей": ("платиновый шнур", "платиновый шнур 250 зм", 250, True),
}
for d in data:
    if d["n"] in COMP:
        k, t, gp, use = COMP[d["n"]]
        d["cm"] = dict(k=k, t=t, gp=gp, use=use)

js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
html = (HERE / "helper_tpl.html").read_text(encoding="utf-8")
html = html.replace("__DATA__", js).replace("__CLS__", json.dumps(CLS, ensure_ascii=False)).replace("__N__", str(len(data)))
html = html.replace("__SEED__", json.dumps(dict(id=seed_id, items=seed, mat=MAT, mid=hashlib.sha1(json.dumps(MAT, ensure_ascii=False).encode()).hexdigest()[:10]), ensure_ascii=False).replace("</", "<\\/"))
out = pathlib.Path(ROOT) / "Помощник варки.html"
out.write_text(html, encoding="utf-8")
print(out, len(data), len(html), seed_id, seed)

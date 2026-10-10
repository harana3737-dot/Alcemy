"""Помощник варки — интерактивная страница игрока: рецепт + ситуация → бонус 5+ и 20, СЛ, партия, шансы;
вкладка «Пояс» — сумка, выпитое, токсичность (8.7), алхимическая концентрация (8.9), отдых.
Не для карточек мастера. Запуск: python3 scripts/cards/helper.py → «Помощник варки.html»."""



def combat_limits(sheet, confirmed):
    """Числа боя из листа; отсутствующие ячейки — явное подтверждение игрока."""
    import re
    def number(pattern):
        match = re.search(pattern, sheet)
        if not match:
            raise ValueError('Ресурсы боя: не найдено однозначное число в листе: ' + pattern)
        return int(match.group(1))
    main = sheet.split('## Основное', 1)[1].split('## Алхимия', 1)[0]
    level = number(r'Чародей (\d+)')
    hp = number(r'- Хиты (\d+),')
    pools = re.search(r'Единиц чародейства (\d+): (\d+) класса \+ (\d+) от Адепта метамагии', main)
    if not pools or int(pools[1]) != int(pools[2]) + int(pools[3]):
        raise ValueError('Ресурсы боя: неоднозначные запасы единиц чародейства')
    costs = dict((int(a), int(b)) for a,b in re.findall(r'^(\d+)-й уровень — (\d+) единиц', sheet, re.M))
    if set(costs) != set(range(1,6)):
        raise ValueError('Ресурсы боя: неполная стоимость создания ячеек')
    if confirmed.get('level') != level or set(confirmed.get('slots', {})) != {'1','2'}:
        raise ValueError('Ресурсы боя: максимумы ячеек требуют подтверждения для этого уровня')
    if any(type(n) is not int or n < 0 for n in confirmed['slots'].values()):
        raise ValueError('Ресурсы боя: неверные максимумы ячеек')
    return dict(level=level, hp=hp, sp=int(pools[2]), meta=int(pools[3]),
                slots=confirmed['slots'], costs=costs)



def bag_discrepancies(sheet, seed):
    """Независимо сверить сумку Талиса с именами и количествами в снаряжении."""
    import re
    from collections import Counter
    equipment = sheet.split('## Снаряжение', 1)[1].split('\n## ', 1)[0]
    expected, actual = Counter(), Counter()
    for heading in ('Зелья и расходники', 'На разборку'):
        block = re.search(r'^' + re.escape(heading) + r'\s*\n((?:•[^\n]*(?:\n|$))+)', equipment, re.M)
        if not block:
            return ['Не найден список «' + heading + '» в снаряжении листа']
        for line in block[1].splitlines():
            name = line.removeprefix('•').strip()
            quantity, unit = 1, ''
            use = re.search(r'\s+\((\d+) исп\.\)$', name)
            if use:
                quantity, unit = int(use[1]), 'исп.'
                name = name[:use.start()]
            else:
                title, separator, count = name.rpartition(' ×')
                if separator:
                    if not count.isdigit():
                        return ['Неоднозначное количество: ' + name]
                    name, quantity = title, int(count)
            expected[(name.strip(), heading == 'На разборку', unit)] += quantity
    errors = []
    for item in seed:
        if item.get('who') != 'p1':
            continue
        if type(item.get('q')) is not int or item['q'] < 0:
            errors.append('Неверное количество в начальной сумке: ' + str(item.get('n')))
            continue
        actual[(item.get('n','').strip(), item.get('note') == 'на разборку', item.get('u',''))] += item['q']
    for key in sorted(expected.keys() | actual.keys()):
        if expected[key] != actual[key]:
            name, disassemble, unit = key
            errors.append(f'{name}' + (' [на разборку]' if disassemble else '') +
                          f': в листе {expected[key]}, в сумке {actual[key]}' + (' ' + unit if unit else ''))
    return errors


def validate_seed(sheet, seed):
    import sys
    errors = bag_discrepancies(sheet, seed)
    if errors:
        print('ПРЕДУПРЕЖДЕНИЕ: сумка по умолчанию расходится с листом:\n  ' + '\n  '.join(errors), file=sys.stderr)
        raise ValueError('Сборка помощника остановлена: проверь названия и количества в исходниках')


def build():
    import hashlib, json, pathlib, re
    HERE = pathlib.Path(__file__).resolve().parent
    import quality
    _g = vars(quality)
    C, CLS, CLS_ORDER, ROOT = _g["C"], _g["CLS"], _g["CLS_ORDER"], _g["ROOT"]

    data = []
    for c in sorted(C, key=lambda c: (c["lvl"], CLS_ORDER.index(c["cls"]), c["name"])):
        b5, b20 = _g["quality"](c)
        data.append(dict(n=c["name"], l=c["lvl"], k=c["cls"], f=c["fam"] or "", e=c["ess"], t=c["tox"], d=c["dur"],
                         p=c["price"], b=c["base"], a=c["stacks_8_9"], s=_g["saves"](c), ar=_g["area"](c) or "", tk=c["tasks"],
                         cc=c["concentration"], up=_g["UPCAST"].get(c["name"], "none"), b5=b5, b20=b20, eff=c["eff"]))

    # Сумка из листа персонажа: блоки «Зелья и расходники» и «На разборку»
    CARD_OF = {"Зелье сопротивления (некротика)": "Сопротивление", "Зелье подводного дыхания": "Водное дыхание"}
    sheet = (pathlib.Path(ROOT) / "Талис — лист персонажа.md").read_text(encoding="utf-8")
    limits = combat_limits(sheet, json.loads((HERE / 'talis_resources.json').read_text(encoding='utf-8')))
    seed, block = [], None
    assert "## Снаряжение" in sheet, "Талис — лист персонажа.md: нет раздела «## Снаряжение»"
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
            if m and m.group(2):
                it["u"] = "исп."  # «Аптечка (10 исп.)» — для блоков LSS
            if n in CARD_OF:
                it["card"] = CARD_OF[n]
            seed.append(it)
    for it in seed:
        it["who"] = "p1"
    # Союзники — по строке «Зелья союзников» в листе
    ALLY = [dict(n="Зелье подводного дыхания", q=1, note="", card="Водное дыхание", who=w) for w in ("pF", "pL")]
    seed += ALLY
    validate_seed(sheet, seed)
    # Материалы Талиса — по блоку «Ингредиенты» листа (сверено 05.10.2026)
    MAT = dict(
        gold=132.58,  # «Монеты» в листе
        herbs=[dict(k="heal", l=1, q=5), dict(k="poison", l=1, q=4)],  # лечебные 1 ур. ×4 + «трава 1.1» ×1; ядовитые 1 ур. ×4 (5 собрано в пещере куа-тоа − 1 на опыт с водорослями; сверено 06.10)
        ess=[dict(id="e1", n="Костяная пыль", types=["Смерть/душа"], l=1, q=1, note=""),
             dict(id="e2", n="Хитин", types=["Чувства", "Тело"], l=1, q=1, note="одна эссенция: Чувства или Тело"),
             dict(id="e3", n="Соль алхимическая", types=["Вода/дыхание"], l=1, q=1, note="годится и как консервант"),
             dict(id="e4", n="Проба крови шахтёра", types=["Тело"], l=2, q=1, st="fresh", note="влажный трофей, законсервирован холодом до 7 дней; вторая у Лаэля")],
        cat=[],
        other=[dict(n="Сырой катализатор I порядка", q=1, note="сначала изготовить (5.3, СЛ 11)"),
               dict(n="Лечебные травы на 60 зм", q=1, note="материалы этапа I Корневой метки, не для варки"),
               dict(n="Ошмётки руды из аномалии", q=1, note="возможно, сырьё для катализатора — порядок у мастера")])

    # Материалы переписаны из листа вручную (там свободный текст) — сверка, чтобы лист и помощник не разошлись
    def sheet_check():
        eq = sheet.split("## Снаряжение", 1)[1]
        ing = eq.split("Ингредиенты", 1)[1].split("\n\n", 1)[0] if "Ингредиенты" in eq else ""
        errs = []
        gm = re.search(r"Монеты:\s*([\d\s]+(?:,\d+)?)\s*зм", eq)
        if not gm or float(gm.group(1).replace(" ", "").replace(",", ".")) != MAT["gold"]:
            errs.append(f"монеты: в листе {gm.group(1) if gm else 'не найдены'}, в MAT {MAT['gold']}")
        num = lambda pat: sum(int(x) for x in re.findall(pat, ing))
        herbs = {(h["k"], h["l"]): h["q"] for h in MAT["herbs"]}
        if num(r"Лечебные травы 1 ур\. ×(\d+)") + num(r"Трава 1\.1 ×(\d+)") != herbs.get(("heal", 1), 0):
            errs.append("лечебные травы 1 ур.")
        if num(r"Ядовитые травы 1 ур\. ×(\d+)") != herbs.get(("poison", 1), 0):
            errs.append("ядовитые травы 1 ур.")
        for x in MAT["ess"] + MAT["other"]:
            if x["n"].split()[0].lower() not in ing.lower():
                errs.append(f"«{x['n']}» нет в блоке «Ингредиенты»")
        if errs:
            raise SystemExit("helper.py: MAT не совпадает с листом персонажа — " + "; ".join(errs) + ". Поправь MAT или лист.")
    sheet_check()
    seed_id = hashlib.sha1(json.dumps([{k: v for k, v in it.items() if k != "u"} for it in seed], ensure_ascii=False).encode()).hexdigest()[:10]

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

    # Вкладки «Свитки» и «Кузня» — шпаргалки ремёсел союзников, встраиваются как есть в теневой DOM (свои стили и id не пересекаются с помощником)
    def craft(fname, host):
        src = (pathlib.Path(ROOT) / fname).read_text(encoding="utf-8")
        css = src.split("<style>", 1)[1].split("</style>", 1)[0]
        body = src.split("</style>", 1)[1].split("<script>", 1)[0]
        body = body[body.index('<div class="wrap">'):]
        code = src.split("<script>", 1)[1].split("</script>", 1)[0].strip()
        for a, b in [(':root:not([data-theme="light"]){', ':host(:not([data-theme="light"])){'), (':root[data-theme="dark"]{', ':host([data-theme="dark"]){'),
                     ("@media print{:root:not(#print){", "@media print{:host{"), (":root{", ":host{"), ("body{", ":host{display:block;")]:
            assert a in css, f"{fname}: в стилях нет «{a}» — поправь craft() в helper.py"
            css = css.replace(a, b, 1)
        css += ('\n:host{--display:"Prata",Georgia,serif;--body:"Golos Text",system-ui,sans-serif;--mono:"JetBrains Mono",ui-monospace,monospace;background:transparent;font-size:15px}'
            "\n.wrap{padding:18px 0 0;max-width:none}")
        assert code.startswith("(function(R){") and code.endswith("})(document);"), f"{fname}: скрипт должен быть (function(R){{…}})(document);"
        code = (code[:-len("(document);")] + "(r);").replace("</", "<\\/")
        doc = json.dumps("<style>" + css + "</style>" + body, ensure_ascii=False).replace("</", "<\\/")
        return (f"(()=>{{const h=document.getElementById('{host}');if(!h||!h.attachShadow)return;const r=h.attachShadow({{mode:'open'}});r.innerHTML={doc};"
            "const th=()=>{const t=document.documentElement.getAttribute('data-theme');t?h.setAttribute('data-theme',t):h.removeAttribute('data-theme')};th();"
            "new MutationObserver(th).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});"
            f"try{{{code}}}catch(e){{console.error(e)}}}})();")
    CRAFTS = craft("Шпаргалка свитков.html", "craft-scroll") + "\n" + craft("Шпаргалка кузнеца.html", "craft-smith")

    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (HERE / "helper_tpl.html").read_text(encoding="utf-8")
    from rules_data import P_SL, NEED, CAT_PRICE
    html = html.replace("__TABLE_PLANNING__", (HERE / "table_planning.js").read_text(encoding="utf-8"))
    html = html.replace("__PLANNING_RULES__", json.dumps(dict(potionDC=P_SL, growth=NEED, catalyst=CAT_PRICE)))
    html = html.replace("__TABLE_COMBINATIONS__", (HERE / "table_combinations.js").read_text(encoding="utf-8"))
    html = html.replace("__TABLE_TOOLS__", (HERE / "table_tools.js").read_text(encoding="utf-8")).replace("__CRAFTS__", CRAFTS)
    from rules_data import helper_values
    for marker, value in helper_values().items():
        html = html.replace(marker, value)
    html = html.replace("__COMBAT_LIMITS__", json.dumps(limits, ensure_ascii=False))
    html = html.replace("__DATA__", js).replace("__CLS__", json.dumps(CLS, ensure_ascii=False)).replace("__N__", str(len(data)))
    html = html.replace("__SEED__", json.dumps(dict(id=seed_id, items=seed, mat=MAT, mid=hashlib.sha1(json.dumps(MAT, ensure_ascii=False).encode()).hexdigest()[:10]), ensure_ascii=False).replace("</", "<\\/"))
    out = pathlib.Path(ROOT) / "Помощник варки.html"
    from generated_files import generated_html
    html = generated_html(html, "scripts/cards/helper.py", "scripts/cards/helper_tpl.html; scripts/cards/table_tools.js; scripts/cards/table_combinations.js; scripts/cards/table_planning.js", version=True)
    out.write_text(html, encoding="utf-8")
    print(out, len(data), len(html), seed_id, seed)


if __name__ == '__main__':
    build()

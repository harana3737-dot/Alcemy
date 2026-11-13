"""Помощник варки — интерактивная страница игрока: рецепт + ситуация → бонус 5+ и 20, СЛ, партия, шансы;
вкладка «Пояс» — сумка, выпитое, токсичность (8.7), алхимическая концентрация (8.9), отдых.
Не для карточек мастера. Запуск: python3 scripts/cards/helper.py → «Помощник варки.html»."""



def combat_limits(sheet, confirmed):
    """Числа боя из листа; отсутствующие ячейки — явное подтверждение игрока."""
    import re
    def number(pattern, text=sheet):
        match = re.search(pattern, text)
        if not match:
            raise ValueError('Ресурсы боя: не найдено однозначное число в листе: ' + pattern)
        return int(match.group(1))
    main = sheet.split('## Основное', 1)[1].split('## Алхимия', 1)[0]
    level = number(r'Чародей (\d+)', main)
    hp = number(r'- Хиты (\d+),', main)
    pools = re.search(r'Единиц чародейства (\d+): (\d+) класса \+ (\d+) от Адепта метамагии', main)
    if not pools or int(pools[1]) != int(pools[2]) + int(pools[3]):
        raise ValueError('Ресурсы боя: неоднозначные запасы единиц чародейства')
    costs = dict((int(a), int(b)) for a,b in re.findall(r'^(\d+)-й уровень — (\d+) единиц', sheet, re.M))
    if set(costs) != set(range(1,6)):
        raise ValueError('Ресурсы боя: неполная стоимость создания ячеек')
    expected_slots = {str(n) for n in range(1, min(9, (level + 1) // 2) + 1)}
    if confirmed.get('level') != level or set(confirmed.get('slots', {})) != expected_slots:
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
    import hashlib, json, pathlib
    HERE = pathlib.Path(__file__).resolve().parent
    from cards_model import prepare_cards, ordered_cards, CLS, ROOT, saves, area
    from quality import quality
    from upcast import UPCAST

    data = []
    for c in ordered_cards(prepare_cards()):
        b5, b20 = quality(c)
        data.append(dict(n=c["name"], l=c["lvl"], k=c["cls"], f=c["fam"] or "", e=c["ess"], t=c["tox"], d=c["dur"],
                         p=c["price"], b=c["base"], a=c["stacks_8_9"], s=saves(c), ar=area(c) or "", tk=c["tasks"],
                         cc=c["concentration"], up=UPCAST.get(c["name"], "none"), b5=b5, b20=b20, eff=c["eff"]))

    # Начальные сумки и материалы — из одного подтверждённого снимка.
    # Работающая сумка браузера по нему автоматически не сбрасывается.
    from current_inventory import seed as inventory_seed
    sheet = (pathlib.Path(ROOT) / 'Талис — лист персонажа.md').read_text(encoding='utf-8')
    limits = combat_limits(sheet, json.loads((HERE / 'talis_resources.json').read_text(encoding='utf-8')))
    seed, MAT = inventory_seed(pathlib.Path(ROOT))
    validate_seed(sheet, seed)
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
        "Силовая клетка": ("рубиновая пыль", "рубиновая пыль 1 500 зм", 1500, False),
        "Священная аура": ("реликварий", "реликварий с реликвией, 1 000 зм", 1000, False),
        "Наблюдение": ("фокус", "фокус на 1 000 зм: хрустальный шар, серебряное зеркало или купель", 1000, False),
        "Связь сущностей": ("платиновый шнур", "платиновый шнур 250 зм", 250, True),
    }
    for d in data:
        if d["n"] in COMP:
            k, t, gp, use = COMP[d["n"]]
            d["cm"] = dict(k=k, t=t, gp=gp, use=use)

    # Вкладки «Свитки» и «Кузня» — шпаргалки ремёсел союзников, встраиваются как есть в теневой DOM (свои стили и id не пересекаются с помощником)
    from craft_embed import embed_craft
    CRAFTS = embed_craft(ROOT, "Шпаргалка свитков.html", "craft-scroll") + "\n" + embed_craft(ROOT, "Шпаргалка кузнеца.html", "craft-smith")

    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (HERE / "helper_tpl.html").read_text(encoding="utf-8")
    from rules_data import P_SL, NEED, CAT_PRICE
    for marker, name in [('STORAGE', 'table_storage.js'), ('COMBAT', 'table_combat.js'), ('MATERIALS', 'table_materials.js')]:
        html = html.replace("__TABLE_" + marker + "__\n", (HERE / name).read_text(encoding="utf-8"))
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
    html = generated_html(html, "scripts/cards/helper.py", "scripts/cards/helper_tpl.html; scripts/cards/table_storage.js; scripts/cards/table_combat.js; scripts/cards/table_materials.js; scripts/cards/table_tools.js; scripts/cards/table_combinations.js; scripts/cards/table_planning.js", version=True)
    out.write_text(html, encoding="utf-8")
    print(out, len(data), len(html), seed_id)


if __name__ == '__main__':
    build()

"""Воспроизводимый прогон; --write создаёт отчёт и CSV, --check сверяет их."""
import argparse
import csv
import hashlib
import io
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
import alchemy_bestiary as a
import bestiary_report as b

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'scripts/alchemy_bestiary'
REPORT = ROOT / 'Алхимия и магия — проверка на бестиарии.md'
FIELDS = ('level', 'monster', 'cr', 'role', 'scenario', 'mastery_min', 'metric', 'value', 'with_lr', 'baseline', 'cost_gp', 'toxicity', 'note')


def calculate():
    a.validate_sources()
    monsters = b.load()
    rows = []
    def row(level, m, role, scenario, mastery, metric, value, lr=None, baseline=None, cost='', tox='', note=''):
        rows.append(dict(zip(FIELDS, (level, m['index'], m['challenge_rating'], role, scenario, mastery,
                                     metric, round(value, 8), '' if lr is None else round(lr, 8),
                                     '' if baseline is None else round(baseline, 8), cost, tox, note))))
    for level in a.LEVELS:
        lo, hi = b.band(level)
        for m in monsters:
            if not lo <= m['challenge_rating'] <= hi:
                continue
            for item in range(1, 11):
                for attacks in (1, 2):
                    normal = a.ordinary_poison(m, item, level, attacks)
                    resistant = a.ordinary_poison(m, item, level, attacks, spend_lr=True)
                    row(level, m, 'носитель', f'Обычный яд {item}; {attacks} атаки', item,
                        'damage_3_rounds', normal['damage'], resistant['damage'], note='Одна доза, максимум пять попыток; без урона оружия и триггеров')
                    row(level, m, 'носитель', f'Обычный яд {item}; {attacks} атаки', item,
                        'trigger_probability', normal['any_trigger'], resistant['any_trigger'])
            for p in a.CONTROLS:
                for quality in (0, 1, 2):
                    x = a.control_metrics(m, p, level, quality)
                    y = a.control_metrics(m, p, level, quality, spend_lr=True)
                    name = p.name + ('', ' [сильный]', ' [мощный]')[quality]
                    for metric, key in (('delivery_probability', 'delivered'), ('active_target_turns', 'turns_delivered')):
                        row(level, m, 'носитель', name, a.CARDS[p.name]['lvl'], metric, x[key], y[key],
                            cost=a.price(p.name), note='Одна атака; нет дополнительного урона, прекращающего контроль; не число потерянных действий')
                if p.name in ('Яд: ментальная тюрьма', 'Яд: слабоумие'):
                    n, sides = (5, 10) if p.circle == 6 else (4, 6)
                    hit = 1 - a.attack_outcomes(m, b.pb(level) + 3)['miss']
                    initial = 0 if a.poison_immunity(m) else hit * b.rolled_damage(n, sides, 0, False, b.multiplier(m, 'psychic'), False)
                    row(level, m, 'носитель', p.name, a.CARDS[p.name]['lvl'], 'initial_damage', initial, initial,
                        note='Психический урон сохраняется при успешном спасброске; без урона оружия')
            for role in ('чародей', 'волшебник'):
                for item, count, sides, types in ((2, 3, 8, ('fire', 'cold', 'acid', 'thunder')), (5, 8, 6, ('fire', 'cold'))):
                    for dtype in types:
                        spec = a.Damage('Склянка', 2 if item == 2 else 3, ((dtype, count, sides),), 'con' if dtype == 'thunder' else 'dex')
                        name = f'Склянка {item}: {dtype}'
                        dmg = a.damage(m, spec, level, role)
                        lr = a.damage(m, spec, level, role, spend_lr=True)
                        row(level, m, role, name, item, 'damage_on_placement', dmg, lr, cost=120 if item == 2 else a.price('Склянка стихии: большая'), tox=0)
                        row(level, m, role, name, item, 'damage_precise_only', dmg * a.precise_throw(level, role), lr * a.precise_throw(level, role),
                            note='Без обучения броску; рассеявшиеся склянки считаются нулём — нижняя оценка для одной цели')
                blast = a.ORB if level == 4 and role == 'чародей' else a.FIREBALL if role == 'волшебник' else a.PSIONIC
                if level == 4 and role == 'волшебник':
                    blast = a.Damage('Волшебная стрела', 1, (('force', 3, 4),))
                    # Автоматическое попадание, 3×(1к4+1); Щит цели отдельно не моделируется.
                    blast_value = lambda lr: 0 if b.immune_spell(m, 1) else 3 * b.rolled_damage(1, 4, 1, False, b.multiplier(m, 'force'), False)
                    max_value = lambda lr: 0 if b.immune_spell(m, 1) else 3 * int(5 * b.multiplier(m, 'force'))
                else:
                    blast_value = lambda lr: a.damage(m, blast, level, role, spend_lr=lr)
                    max_value = lambda lr: a.damage(m, blast, level, role, maximize=True, spend_lr=lr)
                cantrip = a.damage(m, a.cantrip(level, role), level, role)
                base = blast_value(False) + 2 * cantrip
                base_lr = blast_value(True) + 2 * cantrip
                row(level, m, role, 'Заклинание + 2 заговора', 0, 'damage_3_rounds', base, base_lr, base, note=blast.name + '; будущие заклинания — условный сценарий')
                row(level, m, role, 'Максимальная сила + заклинание + 2 заговора', 6, 'damage_3_rounds', max_value(False) + 2 * cantrip,
                    max_value(True) + 2 * cantrip, base, a.price('Максимальная сила'), 3, 'Питьё бонусным действием первого хода; усилено одно настоящее заклинание')
                crown = a.damage(m, a.CROWN, level, role)
                for shots in (2, 3):
                    row(level, m, role, f'Корона + 3 заговора; {shots} выстрела', 7, 'damage_3_rounds', shots * crown + 3 * cantrip,
                        shots * crown + 3 * cantrip, 3 * cantrip, a.price('Звёздная корона'), 3,
                        '3: выпита заранее; 2: питьё занимает бонусное действие первого хода; Метамагия конкурирует за бонусное действие')
                a.validate_loadout(['Максимальная сила', 'Звёздная корона'], level, con=3 if role == 'чародей' else 2, casting=True)
                row(level, m, role, 'Максимальная сила + Корона; подготовлено', 7, 'damage_3_rounds', max_value(False) + 2 * cantrip + 3 * crown,
                    max_value(True) + 2 * cantrip + 3 * crown, base, a.price('Максимальная сила') + a.price('Звёздная корона'), 6,
                    'Оба зелья заранее, заклинание в пределах минуты; 3 бонусных действия для выстрелов')
                if level >= 5:
                    p = a.CONTROL_BY_NAME['Яд: удержание чудовища']
                    combo, ready = a.poison_paralysis_spell(m, level, role, p)
                    combo_lr, _ = a.poison_paralysis_spell(m, level, role, p, True)
                    spec, beams = (a.ORB, 1) if role == 'чародей' else (a.RAY, 3)
                    row(level, m, role, 'Удержание чудовища + атака заклинанием', 5, 'damage_next_cast', combo, combo_lr,
                        beams * a.damage(m, spec, level, role), a.price(p.name), 0,
                        'Свой яд: у чародея кинжал +БМ+2, у волшебника рапира +БМ+3; заклинание в ход 2 после повторного спасброска цели; атака с 5 фт; урон доставки исключён')
                    for all_rolls in (False, True):
                        first = a.damage(m, a.RAZORS, level, role, maximize=True)
                        later = a.damage(m, replace(a.RAZORS, affinity=False), level, role, maximize=all_rolls)
                        row(level, m, role, 'Максимальная сила + лезвия: ' + ('все броски' if all_rolls else 'первый бросок'), 6,
                            'damage_3_contacts', first + 2 * later, baseline=a.damage(m, a.RAZORS, level, role) + 2 * a.damage(m, replace(a.RAZORS, affinity=False), level, role),
                            cost=a.price('Максимальная сила'), tox=3, note='Чувствительность к трактовке длительного заклинания; три контакта условны, ХАР к одному броску')
                if level >= 9:
                    for item in (6, 8, 10):
                        d, probability = a.con_debuff_cone(m, item, level, role)
                        dlr, _ = a.con_debuff_cone(m, item, level, role, True)
                        row(level, m, role, f'Яд {item}: триггер ТЕЛ + Конус холода', item, 'damage_next_cast', d, dlr,
                            a.damage(m, a.CONE, level, role), note='Только вклад триггера ТЕЛ; без прочего урона и остальных 11 триггеров')
                    tele = a.mental_telekinesis(m, level, role=role)
                    tele_lr = a.mental_telekinesis(m, level, True, role=role)
                    row(level, m, role, 'Ментальная тюрьма + Телекинез', 6, 'additional_damage', tele['additional_damage'], tele_lr['additional_damage'], 0,
                        a.price('Яд: ментальная тюрьма'), 0, 'Ход 1: доставка яда; ход 2: проверка без БМ; цель не разрушила иллюзию раньше, размер не больше Huge')
                if role == 'волшебник':
                    attacks = 1 if level < 6 else 2
                    base_weapon = a.weapon_turn(m, level, attacks)
                    for name, mastery, kwargs, cost in (
                        ('Священное масло', 6, dict(holy=True), a.price('Священное масло')),
                        ('Масло остроты', 8, dict(sharp=True), a.price('Масло остроты')),
                        ('Тензер + священное масло', 9, dict(tensor=True, holy=True), a.price('Трансформация Тензера') + a.price('Священное масло'))):
                        n = 2 if kwargs.get('tensor') else attacks
                        row(level, m, role, name, mastery, 'damage_weapon_turn', a.weapon_turn(m, level, n, **kwargs), baseline=base_weapon, cost=cost,
                            tox=4 if kwargs.get('tensor') else 0, note='Устойчивый ход после подготовки; нет затрат действий подготовки в этом числе')
                    if level >= 5:
                        a.validate_loadout(['Трансформация Тензера', 'Священное масло'], level, spell_concentrations=1)
                        row(level, m, role, 'Своё Ускорение → Тензер + священное масло', 9, 'damage_weapon_turn',
                            a.weapon_turn(m, level, 3, tensor=True, holy=True), baseline=a.weapon_turn(m, level, attacks + 1, holy=True),
                            cost=a.price('Трансформация Тензера') + a.price('Священное масло'), tox=4,
                            note='Ускорение наложено до питья; одна настоящая и одна алхимическая концентрация; 2+1 атаки, не 4')
                if level >= 7:
                    trap = a.radiance_trap(m, level)
                    trap_lr = a.radiance_trap(m, level, spend_lr=True)
                    row(level, m, role, 'Склянка клетки + Болезненное сияние', 7, 'exhaustion_death_10_contacts', trap['death'], trap_lr['death'],
                        cost=a.price('Силовая клетка'), tox=0,
                        note='Условно: цель помещается, не телепортируется, нет развеивания/разрыва концентрации; не вероятность победы')
    return monsters, rows


def render(monsters, rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, FIELDS, lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
    csv_text = out.getvalue()
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r['level'], r['role'], r['scenario'], r['metric'])].append(r)
    text = ['# Алхимия и магия — проверка на бестиарии', '',
            '> Расчёт Codex, 7 октября 2026 года. Это проверка сценариев, а не изменение правил или выбранных заклинаний персонажей.', '',
            f'Источник содержит {len(monsters)} закреплённых существ SRD 2014; в уровневых диапазонах рассчитано **{len(rows):,} строк**. Каждый монстр имеет одинаковый вес; это не частота встреч в кампании.', '',
            '## Как читать результаты', '',
            'Весь бестиарий используется для обзора иммунитетов и проверки вероятностей. Подробные прогоны ограничены диапазонами опасности: уровень 4 — CR ¼–6, уровень 5 — 2–8, уровень 8 — 4–12, уровни 11/13 — 8–17, уровни 17/20 — 12–24. Существа CR 0 и CR выше 24 не входят в уровневые средние.', '',
            'Уровни персонажа: 4, 5, 8, 11, 13, 17 и 20. Мастерство алхимии независимо от уровня персонажа: предметы доступны только при мастерстве не ниже `mastery_min`. На 4 уровне актуальное мастерство Талиса — II; остальные рецепты приведены как будущие возможности или покупные предметы.', '',
            'ХАР/ИНТ +4 до уровня 8, затем +5 — условный путь развития. ЛОВ +2 у чародея для броска склянок; +3 у волшебника и носителя рапиры. Это не новые решения о характеристиках. Будущие заклинания в таблицах — тестовые варианты, а не пополнение известных заклинаний.', '',
            'Урон указан по одной цели. Результаты не ограничены её запасом хитов. Учитываются попадания, криты, спасброски, сопротивления и иммунитеты. ЛС — стресс-сценарий: цель расходует легендарное сопротивление на первые провалы. В обычном уроне за 3 хода ЛС на массовое заклинание требуется один раз, остальные действия — атаки заговорами.', '',
            '## Склянки: Сл мага и точность броска', '',
            'Без обучения броску вероятность попасть в выбранную точку КД 10 — 65% у Талиса и 70% у Лаэля, независимо от уровня. В CSV есть урон при правильном размещении и нижняя оценка, где рассеявшийся бросок не задевает цель. По группе площадь может оказаться важнее этой потери точности.', '',
            '## Ключевые сценарии по уровням', '',
            '| Уровень | Существ | Роль | Сценарий | Мастерство | Среднее | С ЛС | База |',
            '| --- | ---:|---|---|---:|---:|---:|---:|']
    selected = {'Максимальная сила + заклинание + 2 заговора', 'Корона + 3 заговора; 2 выстрела',
                'Максимальная сила + Корона; подготовлено', 'Удержание чудовища + атака заклинанием',
                'Тензер + священное масло', 'Своё Ускорение → Тензер + священное масло'}
    mean = lambda rs, field: sum(float(r[field]) for r in rs if r[field] != '') / sum(r[field] != '' for r in rs) if any(r[field] != '' for r in rs) else None
    for (level, role, scenario, metric), rs in grouped.items():
        if scenario not in selected: continue
        fmt = lambda v: '—' if v is None else f'{v:.2f}'
        text.append(f'| {level} | {len(rs)} | {role} | {scenario} | {rs[0]["mastery_min"]} | {fmt(mean(rs,"value"))} | {fmt(mean(rs,"with_lr"))} | {fmt(mean(rs,"baseline"))} |')
    text += ['', '## Конкретные противники на уровне 17', '',
             '| Противник | Сценарий | Метрика | Без ЛС | С ЛС |', '| --- | --- | --- | ---: | ---: |']
    names = {m['index']: m['name'] for m in monsters}
    for r in rows:
        if r['level'] != 17 or r['monster'] not in ('ancient-white-dragon', 'lich', 'rakshasa', 'iron-golem'): continue
        control = r['role'] == 'носитель' and r['scenario'] in ('Яд: удержание чудовища','Яд: ментальная тюрьма','Яд: слово силы — боль') and r['metric'] == 'delivery_probability'
        combo = r['role'] == 'чародей' and r['scenario'] in ('Максимальная сила + Корона; подготовлено','Склянка клетки + Болезненное сияние')
        if control or combo:
            unit = '%' if 'probability' in r['metric'] or 'death' in r['metric'] else ''
            factor = 100 if unit else 1
            v = f'{float(r["value"])*factor:.2f}{unit}'
            lr = '—' if r['with_lr'] == '' else f'{float(r["with_lr"])*factor:.2f}{unit}'
            text.append(f'| {names[r["monster"]]} | {r["scenario"]} | {r["metric"]} | {v} | {lr} |')
    text += ['', '## Обычные яды и склянки', '',
             '| Уровень | Сценарий | Средний урон | С ЛС |', '| --- | --- | ---: | ---: |']
    for (level, role, scenario, metric), rs in grouped.items():
        ordinary = role == 'носитель' and scenario in ('Обычный яд 2; 1 атаки', 'Обычный яд 6; 2 атаки', 'Обычный яд 10; 2 атаки') and metric == 'damage_3_rounds'
        vial = role == 'чародей' and scenario in ('Склянка 2: cold', 'Склянка 2: thunder', 'Склянка 5: fire') and metric == 'damage_precise_only'
        if ordinary or vial:
            text.append(f'| {level} | {scenario} | {mean(rs,"value"):.2f} | {mean(rs,"with_lr"):.2f} |')
    text += ['', 'Обычные яды: три хода, только добавленный урон яда. Склянки: один бросок, консервативный урон с учётом точного размещения. Доза обычного яда действует на пять попыток атак, включая промахи; повторное попадание после активации немедленно обновляет первую волну без нового спасброска. Высокие триггеры вынесены в CSV как вероятности и не прибавлены к этому урону.', '']
    text += ['', 'Для ядов и атак заклинанием сравнивается только следующий бросок заклинания: первая атака с ядом и потерянное действие мага не прибавлены. Оружейные строки — один устойчивый ход после подготовки; остальные основные строки — три хода. Их нельзя сравнивать между собой как одинаковый урон за раунд.', '',
             '## Контрольные яды', '', '| Уровень | Яд | Доставка обычного качества | С ЛС | Ожидаемые активные ходы цели |', '| --- | --- |---:|---:|---:|']
    for (level, role, scenario, metric), rs in grouped.items():
        if role != 'носитель' or metric != 'delivery_probability' or not scenario.startswith('Яд:') or '[' in scenario: continue
        turns = grouped[(level, role, scenario, 'active_target_turns')]
        text.append(f'| {level} | {scenario} | {100*mean(rs,"value"):.1f}% | {100*mean(rs,"with_lr"):.1f}% | {mean(turns,"value"):.3f} |')
    text += ['', '«Активные ходы» не означают потерю всех действий: слепота, луч слабости и слово силы — боль ограничивают разные возможности. Для слепоты горизонт — 10 ходов, для остальных таблица наблюдает первые 3; слабоумие не прекращается через три хода, повторный спасбросок — через 30 дней. При пляске цель может потратить действие на спасбросок в свой первый ход.', '',
             'Внушение требует понимания языка: наличие языка в SRD — лишь верхняя оценка совместимости, общего языка она не доказывает. Смех, внушение и контроль разума здесь не получают дополнительного урона, который даёт повторный спасбросок или прекращает эффект. Проверка «слово силы — боль» использует полные хиты монстра после урона доставляющей рапиры; против уже раненой цели результат будет выше.', '',
             '## Иммунитеты и спорные трактовки', '',
             f'Из 334 существ {sum(a.poison_immunity(m) for m in monsters)} защищены от контрольных ядов иммунитетом к урону ядом или состоянию «отравлен». Для обычного урона блокирует только иммунитет к урону ядом: {sum("poison" in m["damage_immunities"] for m in monsters)} существ. Сопротивление яду само по себе преимущества на спасбросок не даёт.', '',
             'Ракшаса: заряды и склянки считаются исходным заклинанием; его ограниченный иммунитет применяется по исходному кругу. Для контрольного яда правила называют магический эффект, но не явно накладывание заклинания. Основной расчёт допускает эффект яда; если мастер считает его заклинанием, контрольные яды кругов I–VI у ракшаса дают ноль. Телекинез V круга всё равно заблокирован. Это вопрос трактовки, не принятое изменение.', '',
             'Максимальная сила с длительными Застывшими лезвиями: CSV показывает отдельно максимум первого броска и максимум всех трёх контактов. Рекомендация Codex: согласовать трактовку до изготовления. ХАР к холоду добавляется к одному броску заклинания.', '',
             '## Рабочие сочетания и ограничения', '',
             '- Максимальная сила усиливает одно настоящее заклинание до IV круга. Заряды и склянки она не усиливает; Метамагия к ним тоже не применяется.',
             '- Корона даёт атаку бонусным действием. Если выпить её в бою, в первый ход выстрела нет. Ускоренное заклинание конкурирует за то же бонусное действие. Корона и Максимальная сила вместе дают токсичность 6.',
             '- Парализующий яд + атака заклинанием может дать крит с 5 футов, но собственный маг ждёт повторный спасбросок цели. Быстрое союзное попадание до её хода будет сильнее; здесь такого союзника нет.',
             '- Ментальная тюрьма + Телекинез использует противопоставленную проверку ХАР/ИНТ против СИЛ без БМ. Сопротивление магии и ЛС не усиливают эту проверку; ЛС может остановить сам яд. Дополнительные 10к10 условны: иллюзия должна сохраниться до следующего хода.',
             '- Священное масло срабатывает на первом попадании каждого хода. Тензер усиливает каждое попадание, но запрещает новые заклинания. Свое Ускорение нужно наложить до питья; поддерживать его можно. Получается 2 атаки действием + 1 от Ускорения.',
             '- Скорость-зелье + своё Ускорение не складываются. Дополнительное действие Скорости разрешает одну оружейную атаку, а не ещё одно заклинание.',
             '- Скорость-зелье + своё заклинание концентрации допустимы: один эффект алхимической и один настоящей концентрации. Два алхимических эффекта либо два настоящих концентрационных эффекта — недопустимы. На одном оружии одно масло.',
             '- Склянка силовой клетки + Болезненное сияние не требует двух настоящих концентраций. Но расчёт десяти контактов условен: цель должна помещаться и не уходить телепортацией; концентрацию могут сорвать. Смерть от истощения в CSV не равна вероятности выиграть бой.', '',
             '## Рекомендации Codex', '',
             'На текущем IV уровне при мастерстве II сначала сравнивать малую склянку, обычный яд II и доступные контрольные яды по конкретному противнику. Против иммунитета к яду переключаться на стихии и заклинания. На высоких уровнях проверять масло и Корону отдельно от контроля: фиксированная Сл ядов не растёт с уровнем мага. Дорогую клетку использовать только после проверки размеров и способов выхода цели. Рецепты, цены и очередь исследований этим отчётом не изменены.', '',
             '## Дополнение: Метамагия и классовые способности', '',
             'Следующий разбор — «Алхимия — заклинания и метамагия»: Ускоренное заклинание сразу после ядовитого попадания, склянка вместе с Ускоренным заклинанием, Преобразованное и Усиленное, помощь Искусной остротой и способности Песни клинка. В этом срезе исправлен бонус доставки собственного яда чародея: кинжал с Ловкостью +2 вместо общего носителя рапиры с +3.', '',
             '## Воспроизведение', '',
             'Источники: `scripts/bestiary/srd2014-monsters.json`, лицензия `scripts/bestiary/UPSTREAM_LICENSE.md`, карточки `scripts/cards/cards_data.py`, разделы 7.2–7.6 и 8.6–8.11 правил. Старый `sim_poison.py` не используется: его модель сопротивления яду расходится с текущими правилами.', '',
             'Команды: `python3 -B scripts/alchemy_bestiary_report.py --write`, затем `python3 -B scripts/alchemy_bestiary_report.py --check` и `python3 -B -m unittest discover -s scripts -p "test_alchemy_bestiary.py"`. Все построчные результаты: `scripts/alchemy_bestiary/results.csv`.', '',
             f'SHA256 бестиария: `{b.SHA}`.', f'SHA256 CSV: `{hashlib.sha256(csv_text.encode()).hexdigest()}`.', '',
             'Ограничения: нет симуляции ответных атак, сохранения концентрации, перемещения, расхода ячеек всей группы, смертей от обычного урона и вероятности выиграть бой. Поглощение стихий монстром считается нулевым уроном без расчёта лечения. Носитель использует обычную рапиру; её основной урон остаётся немагическим, кроме масла остроты. Триггеры высоких обычных ядов посчитаны как вероятности, без обратной связи остальных 11 эффектов.', '']
    return '\n'.join(text), csv_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true'); parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    monsters, rows = calculate()
    report, csv_text = render(monsters, rows)
    targets = {REPORT: report, DATA / 'results.csv': csv_text}
    if args.check:
        for path, content in targets.items():
            if not path.exists() or path.read_text() != content:
                raise SystemExit('Нужно пересобрать: ' + str(path.relative_to(ROOT)))
    elif args.write:
        DATA.mkdir(exist_ok=True)
        for path, content in targets.items(): path.write_text(content)
    else:
        print(report)
    print(f'Проверено: {len(monsters)} существ, {len(rows)} строк')

if __name__ == '__main__': main()

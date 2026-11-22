"""Сопоставимые программы М2–М5 с одним набором открытий."""
from collections import Counter
from functools import lru_cache
import math

from economy_book import formula_research
from rules_data import BATCH_T, ELIXIR_DC, MB, NEED, P_SL, elixir_batch, proficiency

# Первая карточка каждой группы задаёт цель эксперимента и завершающую варку.
# Группа из одного варианта с False использует уже открытую необычную ступень.
EXPERIMENTS = (
    (2, 'Разум I–II', ('Бдительный отдых',), True),
    (2, 'Движение I–II', ('Шаг сквозь туман', 'Кинетический рывок'), True),
    (3, 'Разум III–V', ('Дрёма', 'Психическая стойкость'), True),
    (3, 'Тело III–V', ('Рост', 'Уменьшение'), True),
    (3, 'Смерть/душа III–V', ('Защита от добра и зла', 'Снятие проклятия'), True),
    (4, 'Разум III–V', ('Чтение мыслей',), False),
    (4, 'Тело III–V', ('Усиленная подмога',), False),
    (4, 'Смерть/душа III–V', ('Защита от смерти',), False),
    (4, 'Чувства III–V', ('Обнаружение существ',), True),
    (4, 'Эфир III–V', ('Преимущество',), True),
)
ROUTES = (
    ('Быстрый', ()),
    ('Смешанный', (0, 2, 3, 5, 6)),
    ('Исследовательский', tuple(range(len(EXPERIMENTS)))),
)


def _add_gain(distribution, outcomes):
    result = Counter()
    for score, p in distribution.items():
        for gain, chance in outcomes.items():
            result[score+gain] += p*chance
    return result


def _outcomes(rolls, bonus, dc, reroll, ordinary):
    if ordinary:
        return 1., {1: 1.}
    success = Counter()
    for face, _, probability in rolls(bonus, dc, int(reroll)):
        if face == 20 or face != 1 and face+bonus >= dc:
            success[2 if face == 20 else 1] += probability
    p = sum(success.values())
    return p, {score: chance/p for score, chance in success.items()}


def _probe_hours(marks, dc, bonus, reroll, ordinary):
    if ordinary:
        return 2*marks
    return 2*formula_research(marks, dc, bonus, None if reroll else 0)[0]


def _serial(needed, dose, size, hours):
    full = {0: 1.}
    for _ in range(size):
        full = _add_gain(full, dose)

    @lru_cache(None)
    def batches(left):
        if left <= 0:
            return 0.
        return (1+sum(p*batches(left-gain) for gain, p in full.items() if gain))/(1-full.get(0, 0))
    return sum(p*batches(left)*hours for left, p in needed.items())


def _night_weeks(hours, ready, weekly, net_bonus):
    if ready is None or ready >= hours:
        return hours/weekly
    return ready/weekly + (hours-ready)/(weekly+net_bonus)


def compare_timing(snapshot, cards, rolls):
    known = snapshot['state'].get('knownRecipes', [])
    bag = Counter()
    for item in snapshot['state']['bag']:
        if item['who'] == 'p1':
            bag[item['n']] += item['q']
    samples = {m: sum(bag[n] for n in (f'Зелье {m}.{m}', f'Зелье лечения {m}.{m}'))
               for m in range(2, 5)}
    start = next(t['current'] for t in snapshot['tracks'] if t['id'] == 'mastery-2-3')
    ink_track = next(t for t in snapshot['tracks'] if t['id'] == 'research-ink')
    if snapshot['settings']['m'] != '2' or ink_track['current'] < ink_track['target']:
        raise ValueError('Пересмотреть исходное мастерство и общий открытый рецепт чернил')
    catalog = {c['name']: c for c in cards}
    for level, _, names, _ in EXPERIMENTS:
        if any(catalog[name]['lvl'] != level or catalog[name]['cls'] != 'eff' for name in names):
            raise ValueError('Изменились выбранные варианты эликсиров')

    def bonus(m):
        return proficiency(5)+MB[m]+3

    def run(label, early, reroll, ordinary, *, skip_ordinary_mind=False, no_sample=False):
        optional = dict(probes=0., first=0., early_practice=0., late_openings=0)
        stages = []
        before = 0.
        ready = None
        # Деление на два ведём в целых полуочках, чтобы честно учитывать чернила.
        for level in (2, 3, 4, 5):
            progress = {2*start if level == 2 else 0: 1.}
            costs = dict(probes=0., first=0., inks=0., serial=0.)
            groups = [i for i, step in enumerate(EXPERIMENTS)
                      if (step[0] if i in early else 5) == level]
            if skip_ordinary_mind and level == 5:
                groups.remove(0)
                groups.insert(groups.index(2)+1, 0)

            for i in groups:
                target, _, names, opens = EXPERIMENTS[i]
                opens = opens and not (skip_ordinary_mind and i == 0)
                if opens:
                    # На М5 можно выбрать ту же, более лёгкую цель II–IV.
                    costs['probes'] += _probe_hours(3 if target <= 2 else 4,
                                                   ELIXIR_DC[target], bonus(level)+2, reroll, ordinary)
                if level < 5 and opens:
                    progress = _add_gain(progress, {2: 1.})
                if level == 5 and opens:
                    optional['late_openings'] += 1
                for name in names:
                    p, gain = _outcomes(rolls, bonus(level), ELIXIR_DC[target]+2, reroll, ordinary)
                    costs['first'] += (2 if target <= 2 else 4)/p
                    if level == target:
                        progress = _add_gain(progress, {2*g: pr for g, pr in gain.items()})
                    if name == 'Бдительный отдых':
                        ready = before+costs['probes']+costs['first']

            optional['probes'] += costs['probes']
            optional['first'] += costs['first']
            if level == 5:
                break

            limit = 2*NEED[level]
            optional_practice = sum(min(score, limit)*p/2 for score, p in progress.items())-(start if level == 2 else 0)
            optional['early_practice'] += optional_practice
            if level == 2:
                p, gain = _outcomes(rolls, bonus(level), ELIXIR_DC[level], reroll, ordinary)
                costs['inks'] = 4/p
                progress = _add_gain(_add_gain(progress, gain), gain)
            if no_sample and level == 4:
                # При том же наборе первых варок добираем освоенным вариантом IV.
                p, gain = _outcomes(rolls, bonus(level), ELIXIR_DC[level], reroll, ordinary)
                size, hours = elixir_batch(level, level), 4
            else:
                if not any(name in known for name in (f'Зелье {level}.{level}', f'Зелье лечения {level}.{level}')):
                    costs['probes'] += _probe_hours(2 if level == 2 else 3, P_SL[level],
                                                    bonus(level)+2, reroll, ordinary)
                    progress = _add_gain(progress, {2: 1.})
                p, gain = _outcomes(rolls, bonus(level), P_SL[level], reroll, ordinary)
                size, hours = BATCH_T[level][level-1], 2
            if max(progress) > limit:
                raise ValueError('Практика нового уровня может начаться внутри сравниваемого этапа')
            remaining = Counter()
            for score, chance in progress.items():
                remaining[max(0, math.ceil((limit-score)/2))] += chance
            pop = sum(min(score, limit)*chance/2 for score, chance in progress.items())-(start if level == 2 else 0)
            costs['serial'] = _serial(remaining, {0: 1-p, **{g: p*pr for g, pr in gain.items()}}, size, hours)
            stages.append(dict(mastery=level, bonus=bonus(level), **costs, total=sum(costs.values()),
                               optional_practice=optional_practice, coincident=pop,
                               serial_practice=NEED[level]-(start if level == 2 else 0)-pop))
            before += stages[-1]['total']

        total = before+costs['probes']+costs['first']
        return dict(label=label, stages=stages, until_m5=before, all_hours=total,
                    research=sum(row['probes'] for row in stages)+costs['probes'],
                    first=optional['first'], serial=sum(row['serial'] for row in stages),
                    inks=stages[0]['inks'], optional=optional, night_ready=ready,
                    weeks={str(w): dict(until_m5=before/w, all=total/w,
                                        night_until_m5=_night_weeks(before, ready, w, 6),
                                        night_all=_night_weeks(total, ready, w, 6),
                                        night_all_if_two_in_base=_night_weeks(total, ready, w, 4))
                           for w in (22, 30)})

    first_independent_iv = next(i for i, (level, _, _, opens) in enumerate(EXPERIMENTS) if level == 4 and opens)
    return dict(start=start, samples=samples, known=known, bonuses={m:bonus(m) for m in range(2, 6)},
                experiments=EXPERIMENTS,
                standard=[run(label, early, False, False) for label, early in ROUTES],
                ordinary=[run(label, early, False, True) for label, early in ROUTES],
                rerolls=[run(label, early, True, False) for label, early in ROUTES],
                without_redundant=run('Быстрый, одна ступень Разума', (), False, False, skip_ordinary_mind=True),
                without_sample=[run(label, early or (first_independent_iv,), False, False, no_sample=True)
                                for label, early in ROUTES])


def _number(value):
    return f'{value:.1f}'.replace('.', ',')


def _table(header, rows):
    return '\n'.join('| '+' | '.join(row)+' |' for row in [header, ['---']*len(header), *rows])


def timing_overview(model):
    rows = []
    for row in model['standard']:
        weeks = [row['weeks'][str(w)] for w in (22, 30)]
        rows.append([row['label'], _number(row['until_m5']), _number(row['all_hours']),
                     ' / '.join(_number(w['until_m5']) for w in weeks),
                     ' / '.join(_number(w['all']) for w in weeks)])
    return _table(['Маршрут', 'До М5, ч', 'До М5 и всего набора, ч',
                   'До М5, недель при 22 / 30 ч', 'До всего набора, недель при 22 / 30 ч'], rows)


def timing_details(model):
    def totals(rows):
        return [[r['label'], *(_number(r[k]) for k in ('research', 'first', 'serial', 'inks', 'until_m5', 'all_hours'))]
                for r in rows]

    header = ['Маршрут', 'Исследования, ч', 'Первые варки, ч', 'Серии ради практики, ч',
              'Чернила II, ч', 'До М5, ч', 'До всего набора, ч']
    stages = []
    for route in model['standard']:
        for row in route['stages']:
            stages.append([route['label'], f"М{row['mastery']} → М{row['mastery']+1}",
                           *(_number(row[k]) for k in ('probes', 'first', 'serial', 'inks', 'total',
                                                       'optional_practice', 'coincident', 'serial_practice'))])
    nights = []
    for route in model['standard']:
        for weekly, weeks in route['weeks'].items():
            nights.append([route['label'], weekly, _number(route['night_ready']),
                           _number(weeks['night_until_m5']), _number(weeks['night_all']),
                           _number(weeks['night_all_if_two_in_base'])])
    practice = [[r['label'], _number(r['optional']['early_practice']),
                 _number(sum(s['coincident'] for s in r['stages'])),
                 _number(sum(s['serial_practice'] for s in r['stages'])), str(r['optional']['late_openings'])]
                for r in model['standard']]
    fallback = [[r['label'], *(_number(r['stages'][-1][k]) for k in ('probes', 'first', 'serial', 'total')),
                 _number(r['until_m5']), _number(r['all_hours'])] for r in model['without_sample']]
    return '\n\n'.join([
        '### Математическое ожидание, без перебросов', _table(header, totals(model['standard'])),
        _table(['Маршрут', 'Из выбранного набора до М5', 'Всего попутно до М5', 'Добрано серийно',
                'Открытия после М5 для М5 → М6'], practice),
        _table(['Маршрут', 'Переход', 'Исследования, ч', 'Первые варки, ч', 'Серии, ч', 'Чернила, ч', 'Всего, ч',
                'Из набора', 'Всего попутно', 'Серийно'], stages),
        '### Все броски дают обычный успех', _table(header, totals(model['ordinary'])),
        '### Чувствительность к Волшебному указанию',
        _table(header, totals(model['rerolls'])),
        '### Если образец 4.4 так и не найден',
        _table(['Маршрут', 'Исследования на М4, ч', 'Первые варки на М4, ч', 'Серии на М4, ч',
                'М4 → М5, ч', 'До М5, ч', 'До всего набора без 4.4, ч'], fallback),
        '### Недели с регулярной рабочей ночью',
        _table(['Маршрут', 'Базовые ч/нед.', 'Первый «Бдительный отдых», ч от старта',
                'До М5, нед.', 'До всего, нед.', 'До всего, нед., если 2 ч уже в базе'], nights),
    ])

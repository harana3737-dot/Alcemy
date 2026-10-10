"""Сверка выбранных действующих таблиц ядра, шпаргалки и экономики с rules.json."""
import argparse
from html.parser import HTMLParser
import math
from pathlib import Path
import re
from rules_data import load_rules, numeric_keys

ROOT = Path(__file__).resolve().parent.parent
CORE = 'Алхимия Талиса — ядро правил.md'
CHEAT = 'Шпаргалка варки.html'
ECONOMY = 'Экономика алхимии — для мастера.md'


def clean(text):
    return re.sub(r'\s+', ' ', text.replace('**', '')).strip()


def markdown_tables(text):
    tables, current = [], []
    for line in text.splitlines() + ['']:
        if line.lstrip().startswith('|'):
            row = [clean(cell) for cell in line.strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?', cell) for cell in row):
                current.append(row)
        elif current:
            tables.append(current)
            current = []
    return tables


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.table, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'table': self.table = []
        elif tag == 'tr' and self.table is not None: self.row = []
        elif tag in ('td', 'th') and self.row is not None: self.cell = []

    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(clean(''.join(self.cell)))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def number(value):
    return float(value.replace(' ', '').replace(',', '.').replace('−', '-'))


def check(root=ROOT, rules_path=None):
    """Никаких записей и генерации; ошибки содержат документ и имя параметра."""
    rules = load_rules(rules_path)
    t = rules['tables']
    herb, dc = numeric_keys(t['HERB']), numeric_keys(t['P_SL'])
    prices = numeric_keys(t['P_PRICE'])
    batches = numeric_keys(t['BATCH_T'])
    errors = []

    def expect(file, parameter, found, expected):
        equal = (math.isclose(found, expected, rel_tol=1e-12, abs_tol=1e-9)
                 if isinstance(found, (int, float)) and isinstance(expected, (int, float))
                 else found == expected)
        if not equal:
            errors.append(f'{file}: {parameter}: найдено {found!r}, ожидается {expected!r}')

    def read(file):
        try: return (Path(root) / file).read_text(encoding='utf-8')
        except OSError as e:
            errors.append(f'{file}: документ не прочитан: {e}')
            return ''

    def table(file, tables, header):
        matches = [rows for rows in tables if rows and rows[0][:len(header)] == header]
        if len(matches) != 1:
            errors.append(f'{file}: таблица {header!r}: найдено {len(matches)}, ожидается одна')
            return []
        return matches[0][1:]

    def row(file, rows, label, values):
        matches = [r[1:] for r in rows if r and r[0] == label]
        if len(matches) != 1:
            errors.append(f'{file}: строка {label!r}: найдено {len(matches)}, ожидается одна')
        else:
            expect(file, label, matches[0], [str(v) for v in values])

    def pattern(file, text, name, regex, values):
        matches = re.findall(regex, text)
        if len(matches) != 1:
            errors.append(f'{file}: {name}: фрагмент не найден однозначно ({len(matches)})')
        else:
            expect(file, name, [number(x) for x in re.findall(r'\d+(?:[.,]\d+)?', matches[0])], values)

    core = read(CORE)
    core_tables = markdown_tables(core)
    rows = table(CORE, core_tables, ['Уровень'] + [str(i) for i in range(1, 11)])
    row(CORE, rows, 'СЛ зелья, яда', list(dc.values()))
    row(CORE, rows, 'СЛ эликсира (+2)', [x + 2 for x in dc.values()])
    row(CORE, rows, 'СЛ чернил', [dc[l] + 2 for l in range(1, 10)] + ['—'])
    row(CORE, rows, 'Катализатор, порядок', [t['ROM'][o] or '—' for o in t['CAT_ORDER_BY_LEVEL'][1:]])
    row(CORE, rows, 'Табличная СЛ / атака применения', list(numeric_keys(t['CARD_TARGET']).values()))
    pattern(CORE, core, 'лестница нестабильности', r'СЛ ([\d, ]+) по порядку', t['INSTAB'])
    pattern(CORE, core, 'объёмы VI–X', r'пока прогресс не наберёт объём: ([^\n]+)', list(dict.fromkeys(numeric_keys(t['WORK_VOLUME']).values())))
    # Из прозы выбираются только параметры формул, не примеры и альтернативы.
    potion_formula = re.search(r'^   - Зелья: (.+)$', core, re.M)
    if potion_formula:
        nums = [int(x) for x in re.findall(r'\d+', potion_formula[1].split('(таблица')[0])]
        expect(CORE, 'формула партии зелий', nums, [1, t['POTION_BATCH_SMALL_M'], t['POTION_BATCH_STEP'], t['POTION_BATCH_OFFSET'], 3, t['POTION_BATCH_OWN'], t['POTION_BATCH_MIN'], t['POTION_BATCH_MAX']])
    else: errors.append(f'{CORE}: формула партии зелий не найдена')
    elixir_formula = re.search(r'^   - Эликсиры: (.+?)\. Только', core, re.M)
    if elixir_formula:
        nums = [int(x) for x in re.findall(r'\d+', elixir_formula[1])]
        low, high = t['ELIXIR_BATCH_CAP']['low'], t['ELIXIR_BATCH_CAP']['high']
        expect(CORE, 'формула партии эликсиров', nums, [t['ELIXIR_BATCH_OFFSET'], low, high, low + 1, high + 1])
    else: errors.append(f'{CORE}: формула партии эликсиров не найдена')

    html = Tables()
    html.feed(read(CHEAT))
    rows = table(CHEAT, html.tables, ['Уровень'] + [str(i) for i in range(1, 11)])
    row(CHEAT, rows, 'Зелья и яды', list(dc.values()))
    row(CHEAT, rows, 'Эликсиры и чернила', [x + 2 for x in dc.values()])
    row(CHEAT, rows, 'Катализатор', [t['ROM'][o] or '—' for o in t['CAT_ORDER_BY_LEVEL'][1:]])
    rows = table(CHEAT, html.tables, ['Применение', '6', '7', '8', '9', '10'])
    row(CHEAT, rows, 'СЛ', t['INSTAB'])
    rows = table(CHEAT, html.tables, ['Мастерство', '1.1', '2.2', '3.3', '4.4', '5.5'])
    for m in range(1, 9): row(CHEAT, rows, str(m), list(batches[m]) + ['—'] * (5 - len(batches[m])))
    row(CHEAT, rows, '9–10', batches[9])
    expect(CHEAT, 'партии мастерства 9 и 10', batches[9], batches[10])
    rows = table(CHEAT, html.tables, ['Место', 'Бонус', 'Потолок зелий'])
    for label, bonus in [('Инструменты', 0), ('Рабочее место', 1), ('Полная лаборатория', 3), ('Мастерская', 5)]:
        row(CHEAT, rows, label, [f'+{bonus}', f"1–{t['PLACE_LIMIT'][str(bonus)]}"])
    rows = table(CHEAT, html.tables, ['Мастерство', 'I', 'II', 'III', 'IV', 'V'])
    expect(CHEAT, 'строк партий эликсиров', len(rows), 6)
    for r in rows:
        m = 6 if r[0] == '6+' else int(r[0])
        for level, cell in enumerate(r[1:], 1):
            if level > m: expect(CHEAT, f'эликсиры {m}/{level}', cell, '—'); continue
            cap = t['ELIXIR_BATCH_CAP']['low' if level <= 2 else 'high']
            base = min(m - level + t['ELIXIR_BATCH_OFFSET'], cap)
            workshop = min(m - level + t['ELIXIR_BATCH_OFFSET'], cap + 1)
            expect(CHEAT, f'эликсиры {m}/{level}', cell, f'{base} ({workshop})' if workshop > base and m >= 3 else str(base))

    economy_tables = markdown_tables(read(ECONOMY))
    rows = table(ECONOMY, economy_tables, ['Зелье', 'СЛ', 'Травы', 'Катализатор на попытку'])
    expect(ECONOMY, 'строк окупаемости', len(rows), 10)
    expect(ECONOMY, 'уровни таблицы окупаемости', [r[0] for r in rows], [f'{l}.{l}' for l in range(1, 11)])
    for r in rows:
        level = int(r[0].split('.')[0])
        expect(ECONOMY, f'СЛ {level}', number(r[1]), dc[level])
        expect(ECONOMY, f'травы {level}', number(r[2]), level * herb[level])
        cat = t['CAT_ORDER_PRICE'][t['CAT_ORDER_BY_LEVEL'][level]]
        expect(ECONOMY, f'катализатор на попытку {level}', number(r[3]), cat / t['CAT_STABLE'])
        expect(ECONOMY, f'цена ×85% {level}', number(r[4]), float(f'{prices[level] * .85:.1f}'))
    rows = table(ECONOMY, economy_tables, ['Катализатор', 'Цена', 'СЛ / бонус'])
    expect(ECONOMY, 'строк катализаторов', len(rows), 4)
    expect(ECONOMY, 'порядки катализаторов', [r[0] for r in rows], t['ROM'][1:5])
    for r in rows:
        order = t['ROM'].index(r[0])
        expect(ECONOMY, f'цена катализатора {r[0]}', number(r[1]), t['CAT_ORDER_PRICE'][order])
        expect(ECONOMY, f'СЛ изготовления {r[0]}', number(r[2].split('/')[0]), t['CAT_DC'][order])
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--rules', type=Path, help='Другой справочник для проверки переноса')
    args = parser.parse_args()
    try: errors = check(args.root, args.rules)
    except (ValueError, KeyError, IndexError, TypeError) as e:
        errors = [f'Изменился формат документа или справочника: {e}']
    print('\n'.join(errors) if errors else 'Справочные числа ядра, шпаргалки и экономики согласованы')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())

"""Сверить применение Ж-148/149, включая переопределения карточек и рабочие документы."""
import argparse
import ast
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'cards'))
from cards_model import prepare_cards, saves

ROOT = Path(__file__).resolve().parent.parent
# Эти повышения названы отдельно за силу эффекта; игрок сохранил их 09.11.2026.
INDEPENDENT = {
    'Защита от добра и зла': 3,
    'Размытый образ': 4,
    'Высшая невидимость, боевая': 8,
    'Трансформация Тензера': 9,
    'Потусторонний облик': 8,
}
DOCUMENTS = (
    'Алхимия Талиса — правила v0.3 (черновик на утверждение).md',
    'Алхимия Талиса — ядро правил.md',
    'Для игрока — книга алхимии.md',
    'Для мастера — сводка варки.md',
    'Для мастера — коротко на утверждение.md',
    'Для мастера — вопросы и изменения.md',
    'Конверсия заклинаний.md',
    'Для игрока — книга экономики.md',
    'Игровые сценарии.md',
    'Недельная варка — расчётные сценарии.md',
    'scripts/cards/gen.py',
    'scripts/cards/helper_tpl.html',
)
# Исторические источники и архивы намеренно не переписываются и здесь не сканируются.
STALE = (
    ('№12', r'Контрольный яд\.\*\*.*до конца 3-го хода'),
    ('№35', r'(?:Камнекожа|Тонкая кожа).*по спасброску.*не (?:увелич|уменьш)'),
    ('№10', r'предварительн\w*.{0,28}20/40|20/40.{0,35}предварительн'),
    ('№2', r'(?:привязк|фиксированные СЛ|изготовители без заклинаний).*(?:не уточн|не утвержд)'),
    ('№2', r'привязк.*к табличной СЛ'),
    ('№8', r'какие варианты.*(?:не уточн|не утвержд)'),
    ('№40', r'Справочная плата — 2 зм|вычитаем 2 зм платы'),
    ('№33', r'(?:Снотворное|Ядовитый плевок).*(?:жд[её]т мастера|карточка — после ответа)'),
)


def check(root=ROOT, cards=None):
    cards = prepare_cards() if cards is None else cards
    by = {c['name']: c for c in cards}
    errors = []
    # Вычисление по исходному заклинанию обнаруживает пропущенные рецепты,
    # а не только сравнивает заранее выбранные восемь названий.
    for c in cards:
        if c['cls'] != 'eff' or c['off'] or 'концентраци' not in c['src_raw']:
            continue
        m = re.search(r'(\d+) ур\.', c['src_raw'])
        if not m:
            continue
        expected = INDEPENDENT.get(c['name'], int(m[1]))
        if c['lvl'] != expected:
            errors.append(f"№41: {c['name']}: уровень {c['lvl']}, требуется {expected}; неперенесённое решение или незафиксированная отдельная надбавка")
        # Концентрация снята, но длительность уже указана в самом источнике.
        duration = re.search(r'(\d+) (минут\w*|час\w*)\)', c['src_raw'])
        if duration and c['dur'] != duration[0][:-1]:
            # Единственное число минуты/часа в русском выводе склоняется иначе.
            n, unit = int(duration[1]), duration[2]
            actual = re.fullmatch(r'(\d+) (минут\w*|час\w*)', c['dur'])
            if not actual or int(actual[1]) != n or (actual[2].startswith('час') != unit.startswith('час')):
                errors.append(f"№3/4: {c['name']}: длительность {c['dur']}, в источнике {duration[0][:-1]}")
    for name, expected in INDEPENDENT.items():
        if name not in by or by[name]['lvl'] != expected:
            errors.append(f'Уточнение игрока: отдельное повышение {name} до {expected} должно сохраняться')
    love, breath = by.get('Любовный напиток'), by.get('Бутилированное дыхание')
    if not love or not love['tox'].startswith('1 ') or love['soft']:
        errors.append('№18: Любовный напиток — токсичность 1, не мягкий')
    if not breath or not re.search(r'«Задержать» — 1\b', breath['tox']) or breath['soft_variants'].get('Задержать') is not False:
        errors.append('№18: Задержать дыхание — токсичность 1, не мягкий вариант')
    monster = by.get('Контроль разума: чудовище')
    if not monster or monster['cls'] != 'psn':
        errors.append('№34: Контроль разума: чудовище — варимый контрольный яд')
    sleep = by.get('Яд: усыпление')
    if not sleep or sleep['cls'] != 'psn' or sleep['lvl'] != 1 or saves(sleep) != 'нет' or '5к8' not in sleep['eff']:
        errors.append('№33: отсутствует контрольный яд Усыпление I с порогом 5к8 без спасброска')
    for c in cards:
        if re.search(r'фиксированная СЛ.*не уточня', c.get('note') or ''):
            errors.append(f"№2: {c['name']}: устаревшее примечание о фиксированной СЛ")
        if c['cls'] == 'psn' and 'до конца 3-го хода' in c['dur']:
            errors.append(f"№12: {c['name']}: срок 3 хода назначен без выбора разрешённого варианта")
    for filename in DOCUMENTS:
        p = Path(root) / filename
        if not p.exists():
            errors.append(f'Не найден рабочий источник {filename}')
            continue
        table_header = None
        for line_number, line in enumerate(p.read_text().splitlines(), 1):
            cells = [x.strip() for x in line.strip('|').split('|')]
            if line.lstrip().startswith('|'):
                if table_header is None:
                    table_header = cells
            else:
                table_header = None
            if table_header and len(table_header) >= 2 and table_header[1] in {'Ур.', 'Уровень'} and len(cells) >= 2 and cells[0] in by and re.fullmatch(r'X|IX|VIII|VII|VI|V|IV|III|II|I', cells[1]):
                from cards_model import ROM
                if cells[1] != ROM[by[cells[0]]['lvl']]:
                    errors.append(f'{filename}:{line_number}: уровень {cells[0]} в рабочей таблице отстал от карточки')
            for clause, pattern in STALE:
                if re.search(pattern, line, re.I):
                    errors.append(f'{filename}:{line_number}: {clause}: устаревшая формулировка')
    short = Path(root) / 'Для мастера — коротко на утверждение.md'
    if short.exists():
        shown = {int(n) for n in re.findall(r'^\| (\d+) \|', short.read_text(), re.M)}
        if shown & {4, 23, 26, 34}:
            errors.append('Пульт повторно спрашивает уже отвеченные №4/23/26/34')
    helper = Path(root) / 'scripts/cards/helper.py'
    if helper.exists():
        component = None
        for node in ast.walk(ast.parse(helper.read_text())):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'COMP' for t in node.targets):
                component = ast.literal_eval(node.value)
        if not component or component.get('Силовая клетка', (None,)*4)[3] is not False:
            errors.append('№28: рубиновая пыль должна быть многоразовым инструментом в учёте материалов')
    else:
        errors.append('Не найден исходник помощника для проверки №28')
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    errors = check()
    if errors:
        raise SystemExit('\n'.join(errors))
    print('Ж-148/149: уровни без надбавки за концентрацию, независимые повышения, сроки, токсичность, компоненты и статусы согласованы')

"""Пересчитать пять таблиц недельного бюджета, сохранив игровые заметки.

Запуск: python3 -B scripts/weekly_economy_report.py --write.
Проверочная сборка — только во временной копии репозитория.
"""
import argparse
from pathlib import Path
import re
import random
import sim_plan as p
from generated_files import marker

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'Недельная варка — план и бюджет.md'
NOTE = marker('scripts/weekly_economy_report.py', 'scripts/sim_plan.py; scripts/rules_data.py', partial=True)


def number(x, digits=1):
    return f'{x:.{digits}f}'.rstrip('0').rstrip('.').replace('.', ',') if digits else f'{x:.0f}'


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                       '| ' + ' | '.join('---' for _ in headers) + ' |',
                       *['| ' + ' | '.join(row) + ' |' for row in rows]])


def replace_table(text, heading, replacement):
    start = text.index(heading) + len(heading)
    match = re.search(r'(?m)^\|[^\n]*(?:\n\|[^\n]*)*', text[start:])
    if not match:
        raise ValueError('Не найдена таблица: ' + heading)
    a, b = start + match.start(), start + match.end()
    return text[:a] + NOTE + '\n' + replacement + text[b:]


def build():
    rng = random.Random(20261008)
    rates = {m: p.per_hour(m, rng=rng) for m in range(2, 11)}
    text = SOURCE.read_text(encoding='utf-8').replace(NOTE + '\n', '')
    text = re.sub(r'^\d{2}\.\d{2}\.\d{4}\.(?: Пересчёт Codex\.)?',
                  '08.10.2026. Пересчёт Codex.', text, count=1, flags=re.M)
    for heading, fn, headers, last in (
        ('### Набор чернил для Лаэля:', p.ink_set, ['Мастерство Талиса', 'I', 'II', 'III', 'IV', 'V'], 5),
        ('### Эликсир-эффект для себя:', p.elixir, ['Мастерство', 'I', 'II', 'III', 'IV', 'V'], 5),
        ('### Зелье лечения для себя:', p.potion, ['Мастерство', '1.1', '2.2', '3.3', '4.4', '5.5', '6.6', '7.7', '8.8'], 8),
    ):
        rows = []
        for m in range(2, 11):
            row = [str(m) + (' (сейчас)' if m == 2 else '')]
            for level in range(1, last + 1):
                if level > m and fn is not p.ink_set:
                    row.append('—'); continue
                result = fn(m, level)
                row.append(number(result[0]) + ' ч / ' + number(result[1], 2) + (' *' if level > m else ''))
            rows.append(row)
        text = replace_table(text, heading, table(headers, rows))
    income = []
    for m, r in rates.items():
        vol = r['vol']
        income.append([str(m), f"+{p.TALIS[m]}", number(r['pot']) + ' зм/ч',
                       number(r['ink'][0]) + ' (' + r['ink'][1] + ')',
                       number(vol[0]) + f' ({vol[1]}, ≈{number(vol[2])} ч)' if vol else '—'])
    text = replace_table(text, '## Что выгодно варить на продажу', table(
        ['Мастерство', 'Бонус', 'Лучшие зелья', 'Лучшие чернила / заряды I–V', 'Объём работы VI+'], income))
    rows = []
    configurations = [(2,2,2,2), (3,3,2,3), (4,4,2,4), (5,4,3,5), (6,5,3,5), (7,5,3,5), (8,5,4,5), (9,5,4,5)]
    for m, ink, kit, heal in configurations:
        choices = [p.week(m, ink, kit, heal, h, income=rates[m]) for h in (12,22,30)]
        r = choices[0]
        gold = sum(r[k][1] for k in ('ink', 'kit', 'heal'))
        result = []
        for w in choices:
            if not w['fits_expected_budget']:
                result.append('не хватает ' + number(w['shortfall_hours']) + ' ч')
            else:
                result.append('+' + number(w['free']) + ' ч продажи: +' + number(w['sale'], 0) + ' зм')
        rows.append([f'Мастерство {m}', f"чернила {p.ROM[ink]} ×2,5 + 3 эликсира {p.ROM[kit]} + 4 зелья {heal}.{heal}",
                     number(r['fixed']), number(gold, 0), *result])
    text = replace_table(text, '## Примеры недели', table(
        ['Ступень', 'Что', 'Часов', 'Золото', '12 ч', '22 ч', '30 ч'], rows))
    text = text.replace('У них доход 18–270 зм в час на I–V и до ≈425 на VI+. Зелья на продажу дают 3–65 зм в час,',
                        'Доход зависит от бонуса и уровня; актуальные значения — в таблице ниже. Зелья на продажу дают меньше,')
    text = text.replace('- **Зелья не догоняют чернила ни на одной ступени**: в 2–7 раз меньше в час (разрыв меньше всего на мастерстве 3).',
                        '- **Сравнивай доход по строке своего мастерства.** Партии простых зелий продолжают расти до мастерства 10; высокая ступень не превращает дозы 6.6+ в партии.')
    text = text.replace('С 6 — V, пока объём работы VI+ не станет выгоднее: на мастерстве 8 сравниваются, на 9 VII уже лучше.',
                        'С 6 сравнивай чернила V с объёмом работы VI+ по актуальной таблице; это сценарий доступных рецептов и рабочего места.')
    text = text.replace('в колонке «стандарт» — доля без −2.',
                        'качество набора здесь не превращено в отдельную цену.')
    notice = ('**Как читать расчёты после пересборки.** Все часы — ожидания, без округления до целых партий. '
              'Поле fits_expected_budget сравнивает ожидание с бюджетом; shortfall_hours показывает нехватку часов. '
              'Положительный результат не гарантирует завершение конкретной недели. Осечки, ремонт, оборудование и оборотный капитал не вычтены из прибыли. '
              'Эликсиры в таблице — стандартный рецепт своего уровня; особые эссенции и расходуемые компоненты проверяй по карточке.\n\n')
    if '**Как читать расчёты после пересборки.**' in text:
        text = re.sub(r'\*\*Как читать расчёты после пересборки\.\*\*[^\n]*\n\n', notice, text, count=1)
    else:
        text = text.replace('## Коротко\n\n', '## Коротко\n\n' + notice, 1)
    return text


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    result = build()
    if args.write:
        SOURCE.write_text(result, encoding='utf-8')
        print('Обновлены пять таблиц недельного бюджета; игровые заметки сохранены.')
    else:
        print(result)
